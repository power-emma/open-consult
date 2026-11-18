#!/usr/bin/env python3
"""Reconstruct an observable 16x16 bank-1 lookup surface from C9 trace CSVs.

This is an oracle for *behaviour*, not a ROM-byte dumper.  It fits the bank-0
value observed after the unread bank-1 lookup.  Cells without enough weighted
observations are emitted as null and must not be treated as recovered bytes.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "rom" / "23710-2L904_1000-FFFF.bin"

PROFILES = {
    "timing": {
        "glob": "*_table-trace.csv",
        "target": "timing_base_signed_candidate",
        "rpm_axis": 0x1F00,
        "load_axis": 0x1F10,
    },
    "fuel": {
        "glob": "*_fuel-trace.csv",
        "target": "fuel_0a74_byte_raw",
        "rpm_axis": 0x1900,
        "load_axis": 0x1910,
    },
}


def rom_bytes(address, size=16, path=ROM):
    data = path.read_bytes()
    start = address - 0x1000
    if start < 0 or start + size > len(data):
        raise ValueError(f"ROM does not contain ${address:04X}..${address+size-1:04X}")
    return list(data[start:start + size])


def interval(axis, value):
    """Return the clamped interpolation interval and fraction."""
    if value <= axis[0]:
        return 0, 0.0
    if value >= axis[-1]:
        return len(axis) - 2, 1.0
    for index in range(len(axis) - 1):
        if axis[index] <= value <= axis[index + 1]:
            width = axis[index + 1] - axis[index]
            if width <= 0:
                raise ValueError("axis values must be strictly increasing")
            return index, (value - axis[index]) / width
    raise AssertionError("unreachable interval")


def weights(rpm_axis, load_axis, rpm, load):
    row, rf = interval(rpm_axis, rpm)
    col, cf = interval(load_axis, load)
    result = np.zeros(256, dtype=float)
    result[row * 16 + col] = (1 - rf) * (1 - cf)
    result[(row + 1) * 16 + col] = rf * (1 - cf)
    result[row * 16 + col + 1] = (1 - rf) * cf
    result[(row + 1) * 16 + col + 1] = rf * cf
    return result


def read_samples(paths, target):
    grouped = defaultdict(list)
    rows = 0
    for path in paths:
        with path.open(newline="") as stream:
            for record in csv.DictReader(stream):
                rows += 1
                try:
                    rpm = float(record["rpm_index_raw"])
                    load = float(record["load_code"])
                    value = float(record[target])
                except (KeyError, TypeError, ValueError):
                    continue
                if all(math.isfinite(v) for v in (rpm, load, value)):
                    grouped[(rpm, load)].append(value)
    samples = [(rpm, load, float(np.median(values)), len(values))
               for (rpm, load), values in sorted(grouped.items())]
    return samples, rows


def fit(samples, rpm_axis, load_axis, divisor, ridge=0.25):
    matrix = np.vstack([weights(rpm_axis, load_axis, rpm, load / divisor)
                        for rpm, load, _, _ in samples])
    observed = np.array([value for _, _, value, _ in samples], dtype=float)
    repeats = np.array([count for _, _, _, count in samples], dtype=float)
    # Repeats improve confidence sublinearly so a long idle does not dominate.
    scale = np.sqrt(np.minimum(repeats, 25.0))
    weighted_matrix = matrix * scale[:, None]
    weighted_values = observed * scale
    regularizer = math.sqrt(ridge) * np.eye(256)
    solution, _, rank, _ = np.linalg.lstsq(
        np.vstack((weighted_matrix, regularizer)),
        np.concatenate((weighted_values, np.zeros(256))), rcond=None)
    predicted = matrix @ solution
    error = predicted - observed
    support = matrix.T @ np.minimum(repeats, 25.0)
    return {
        "solution": solution,
        "support": support,
        "rank": int(rank),
        "rmse": float(np.sqrt(np.mean(error ** 2))),
        "mae": float(np.mean(np.abs(error))),
    }


def serialise_grid(values, support, minimum_support):
    grid = []
    support_grid = []
    for row in range(16):
        out_row = []
        support_row = []
        for col in range(16):
            index = row * 16 + col
            amount = float(support[index])
            support_row.append(round(amount, 3))
            out_row.append(round(float(values[index]), 3)
                           if amount >= minimum_support else None)
        grid.append(out_row)
        support_grid.append(support_row)
    return grid, support_grid


def display_path(path):
    """Keep repository inputs portable while preserving external paths."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="*", type=Path,
                        help="trace CSVs (default: matching logs for the profile)")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="timing")
    parser.add_argument("--load-divisor", type=float, default=256.0,
                        help="convert raw load_code to the table coordinate (default: 256)")
    parser.add_argument("--ridge", type=float, default=0.25)
    parser.add_argument("--minimum-support", type=float, default=1.0)
    parser.add_argument("--output", type=Path,
                        help="JSON output (default: output/bank1-<profile>-oracle.json)")
    args = parser.parse_args(argv)
    if not math.isfinite(args.load_divisor) or args.load_divisor <= 0:
        parser.error("--load-divisor must be finite and positive")
    if not math.isfinite(args.ridge) or args.ridge < 0:
        parser.error("--ridge must be finite and nonnegative")
    if not math.isfinite(args.minimum_support) or args.minimum_support < 0:
        parser.error("--minimum-support must be finite and nonnegative")

    profile = PROFILES[args.profile]
    paths = args.csv or sorted((ROOT / "logs").glob(profile["glob"]))
    if not paths:
        parser.error("no matching trace CSV files")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        parser.error("missing CSV: " + ", ".join(missing))

    rpm_axis = rom_bytes(profile["rpm_axis"])
    load_axis = rom_bytes(profile["load_axis"])
    samples, raw_rows = read_samples(paths, profile["target"])
    if len(samples) < 4:
        parser.error("fewer than four usable coordinate groups")
    result = fit(samples, rpm_axis, load_axis, args.load_divisor, args.ridge)
    grid, support = serialise_grid(result["solution"], result["support"],
                                   args.minimum_support)
    recovered = sum(cell is not None for row in grid for cell in row)
    document = {
        "kind": "behavioural_bank1_lookup_oracle",
        "warning": "Fitted observable surface, not ROM bytes. Null cells are unsupported.",
        "profile": args.profile,
        "target": profile["target"],
        "sources": [display_path(path) for path in paths],
        "raw_rows": raw_rows,
        "unique_coordinate_groups": len(samples),
        "load_divisor": args.load_divisor,
        "ridge": args.ridge,
        "minimum_support": args.minimum_support,
        "rpm_axis_raw": rpm_axis,
        "load_axis_raw": load_axis,
        "matrix_rank_with_regularizer": result["rank"],
        "training_rmse": result["rmse"],
        "training_mae": result["mae"],
        "supported_cells": recovered,
        "total_cells": 256,
        "grid": grid,
        "support": support,
    }
    output = args.output or ROOT / "output" / f"bank1-{args.profile}-oracle.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + "\n")
    print(f"Wrote {output}")
    print(f"Rows {raw_rows}; coordinate groups {len(samples)}; supported cells {recovered}/256")
    print(f"Fit RMSE {result['rmse']:.3f}; MAE {result['mae']:.3f}")
    print("This is a behavioural surface, not a byte-exact bank-1 dump.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
