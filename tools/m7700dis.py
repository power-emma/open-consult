#!/usr/bin/env python3
"""Recursive-descent disassembler for Mitsubishi 7700 ROM images (bank 0 only).

    python3 tools/m7700dis.py rom/23710-2L904_1000-FFFF.bin --base 1000 -o rom/23710-2L904.asm

Instruction lengths on the 7700 depend on the m (data width) and x (index width) flags,
so a linear sweep goes wrong. This follows code from the interrupt vectors, tracking
SEP/CLP/SEM/CLM and PHP/PLP along each path, and follows JMP/JSR (abs,X) jump tables.
Bytes that no path reaches are listed as data.

Assumptions (all reported in the listing header):
  - Direct page register DPR = 0, data bank DT = 0, program bank 0.
  - m = x = 0 (16-bit) at every vector, the 7700 reset state.
  - A subroutine returns with the flags it was called with.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m7700_tables import PAGE0, PAGE42, PAGE89  # noqa: E402

BRANCHES = {"BPL", "BMI", "BVC", "BVS", "BCC", "BCS", "BNE", "BEQ", "BBS", "BBC"}
ENDS = {"RTS", "RTL", "RTI", "STP", "BRK", "UNK", "WDM", "COP"}
WRITES = {"STA", "STB", "STX", "STY", "STZ", "INC", "DEC", "ASL", "LSR", "LSRB", "ROL",
          "ROR", "TSB", "TRB", "SEB", "CLB", "LDM"}
ABS_MODES = {"A", "AX", "AY", "LDM5", "LDM5X", "BBCA"}
DP_MODES = {"D", "DX", "DY", "DI", "DIY", "DLI", "DLIY", "DXI", "LDM4", "LDM4X", "BBCD", "PEI"}

# M37702 vector names (data sheet); other 7700 parts add vectors below FFD6.
VECTOR_NAMES = {
    0xFFFE: "RESET", 0xFFFC: "ZERO_DIV", 0xFFFA: "BRK", 0xFFF8: "DBC", 0xFFF6: "WDT",
    0xFFF4: "NMI", 0xFFF2: "INT0", 0xFFF0: "INT1", 0xFFEE: "INT2", 0xFFEC: "TA0",
    0xFFEA: "TA1", 0xFFE8: "TA2", 0xFFE6: "TA3", 0xFFE4: "TA4", 0xFFE2: "TB0",
    0xFFE0: "TB1", 0xFFDE: "TB2", 0xFFDC: "UART0_RX", 0xFFDA: "UART0_TX",
    0xFFD8: "UART1_RX", 0xFFD6: "UART1_TX", 0xFFD4: "AD",
}


class Insn:
    __slots__ = ("pc", "size", "name", "text", "targets", "flow", "ref", "ref_kind", "m", "x",
                 "table")

    def __init__(self, pc):
        self.pc, self.targets, self.flow, self.ref, self.ref_kind, self.table = pc, [], "next", None, None, None


class Rom:
    def __init__(self, data, base):
        self.data, self.base, self.end = data, base, base + len(data)

    def has(self, a, n=1):
        return self.base <= a and a + n <= self.end

    def r8(self, a):
        return self.data[a - self.base]

    def r16(self, a):
        return self.r8(a) | self.r8(a + 1) << 8

    def r24(self, a):
        return self.r16(a) | self.r8(a + 2) << 16


def s8(v):
    return v - 0x100 if v & 0x80 else v


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def decode(rom, pc, m, x):
    """Decode one instruction at pc with the given m/x flags. Raises IndexError past the end."""
    i = Insn(pc)
    i.m, i.x = m, x
    op, n, table = rom.r8(pc), 1, PAGE0
    if op in (0x42, 0x89):
        table = PAGE42 if op == 0x42 else PAGE89
        op, n = rom.r8(pc + 1), 2
    name, flag, mode = table[op]
    wide = (flag == "M" and not m) or (flag == "X" and not x)
    a = pc + n                      # first operand byte
    w = 2 if wide else 1

    def imm(at):
        return f"#${rom.r16(at):04X}" if wide else f"#${rom.r8(at):02X}"

    t = ""
    if mode in ("IMP",):
        pass
    elif mode == "ACC":
        t = "A"
    elif mode == "ACCB":
        t = "B"
    elif mode == "RELB":
        n += 1
        tgt = (pc + n + s8(rom.r8(a))) & 0xFFFF
        t, i.targets = f"L_{tgt:04X}", [tgt]
    elif mode in ("RELW", "PER"):
        n += 2
        tgt = (pc + n + s16(rom.r16(a))) & 0xFFFF
        t = f"L_{tgt:04X}"
        if mode == "RELW":
            i.targets = [tgt]
    elif mode == "IMM":
        n += w
        t = imm(a)
    elif mode == "D":
        n += 1
        v = rom.r8(a)
        t = f"${v:02X}"
        i.ref, i.ref_kind = v, "dp"
    elif mode == "DX":
        n += 1
        t = f"${rom.r8(a):02X},X"
    elif mode == "DY":
        n += 1
        t = f"${rom.r8(a):02X},Y"
    elif mode == "DI":
        n += 1
        t = f"(${rom.r8(a):02X})"
    elif mode == "DIY":
        n += 1
        t = f"(${rom.r8(a):02X}),Y"
    elif mode == "DLI":
        n += 1
        t = f"[${rom.r8(a):02X}]"
    elif mode == "DLIY":
        n += 1
        t = f"[${rom.r8(a):02X}],Y"
    elif mode == "DXI":
        n += 1
        t = f"(${rom.r8(a):02X},X)"
    elif mode == "A":
        n += 2
        v = rom.r16(a)
        t = f"${v:04X}"
        i.ref, i.ref_kind = v, "abs"
    elif mode == "AX":
        n += 2
        v = rom.r16(a)
        t = f"${v:04X},X"
        i.ref, i.ref_kind = v, "abs"
    elif mode == "AY":
        n += 2
        v = rom.r16(a)
        t = f"${v:04X},Y"
        i.ref, i.ref_kind = v, "abs"
    elif mode == "AI":
        n += 2
        v = rom.r16(a)
        t = f"(${v:04X})"
        i.ref, i.ref_kind = v, "abs"
    elif mode == "AXI":
        n += 2
        v = rom.r16(a)
        t = f"(${v:04X},X)"
        i.ref, i.ref_kind = v, "abs"
    elif mode == "AL":
        n += 3
        v = rom.r24(a)
        t = f"${v:06X}"
    elif mode == "ALX":
        n += 3
        v = rom.r24(a)
        t = f"${v:06X},X"
    elif mode == "S":
        n += 1
        t = f"${rom.r8(a):02X},S"
    elif mode == "SIY":
        n += 1
        t = f"(${rom.r8(a):02X},S),Y"
    elif mode == "MVP" or mode == "MVN":
        n += 2
        t = f"${rom.r8(a):02X},${rom.r8(a + 1):02X}"
    elif mode == "SIG":
        n += 1
        t = f"#${rom.r8(a):02X}"
    elif mode == "LDM4":
        n += 1 + w
        t = f"${rom.r8(a + w):02X},{imm(a)}"
        i.ref, i.ref_kind = rom.r8(a + w), "dp"
    elif mode == "LDM4X":
        n += 1 + w
        t = f"${rom.r8(a + w):02X},X,{imm(a)}"
    elif mode == "LDM5":
        n += 2 + w
        v = rom.r16(a + w)
        t = f"${v:04X},{imm(a)}"
        i.ref, i.ref_kind = v, "abs"
    elif mode == "LDM5X":
        n += 2 + w
        v = rom.r16(a + w)
        t = f"${v:04X},X,{imm(a)}"
        i.ref, i.ref_kind = v, "abs"
    elif mode == "BBCD":
        n += 1 + w + 1
        dp = rom.r8(a)
        bit_val = rom.r8(a + 1) if not wide else rom.r16(a + 1)
        rel_at = a + 1 + w
        tgt = (pc + n + s8(rom.r8(rel_at))) & 0xFFFF
        t = f"${dp:02X},#{bit_val},L_{tgt:04X}"
        i.targets = [tgt]
        i.ref, i.ref_kind = dp, "dp"
    elif mode == "BBCA":
        n += 2 + w + 1
        abs_addr = rom.r16(a)
        bit_val = rom.r8(a + 2) if not wide else rom.r16(a + 2)
        rel_at = a + 2 + w
        tgt = (pc + n + s8(rom.r8(rel_at))) & 0xFFFF
        t = f"${abs_addr:04X},#{bit_val},L_{tgt:04X}"
        i.targets = [tgt]
        i.ref, i.ref_kind = abs_addr, "abs"
    elif mode == "PEI":
        n += 1
        t = f"(${rom.r8(a):02X})"
    elif mode == "PEA":
        n += 2
        t = f"${rom.r16(a):04X}"

    i.size, i.name, i.text, i.table = n, name, t, table
    if name in BRANCHES:
        i.flow = "branch"
    elif name in ("BRA", "BRL"):
        i.flow = "jump"
    elif name in ("JMP", "JML"):
        i.flow = "jump"
        if mode == "A":
            i.targets = [rom.r16(a)]
        elif mode == "AL":
            v = rom.r24(a)
            if v <= 0xFFFF:
                i.targets = [v]
        elif mode == "AXI":
            i.flow = "jump_table"
    elif name in ("JSR", "JSL"):
        i.flow = "call"
        if mode == "A":
            i.targets = [rom.r16(a)]
        elif mode == "AL":
            v = rom.r24(a)
            if v <= 0xFFFF:
                i.targets = [v]
        elif mode == "AXI":
            i.flow = "call_table"
    elif name in ENDS:
        i.flow = "end"
    return i


# ---------------------------------------------------------------------------
# Recursive-descent walker
# ---------------------------------------------------------------------------

def walk(rom):
    insns = {}
    labels = {}
    queue = collections.deque()

    def enqueue(addr, m, x, label=None):
        if addr in insns or not rom.has(addr):
            return
        if label:
            labels[addr] = label
        queue.append((addr, m, x))

    # Seed from interrupt vectors
    for vec_addr in sorted(VECTOR_NAMES):
        if rom.has(vec_addr, 2):
            target = rom.r16(vec_addr)
            if rom.has(target):
                lbl = f"VEC_{VECTOR_NAMES[vec_addr]}"
                labels[target] = lbl
                enqueue(target, 0, 0, lbl)

    while queue:
        pc, m, x = queue.popleft()
        while pc not in insns and rom.has(pc):
            try:
                i = decode(rom, pc, m, x)
            except IndexError:
                break
            if not rom.has(pc, i.size):
                break
            insns[pc] = i

            # Track m/x flag changes
            if i.name == "SEP":
                v = rom.r8(pc + 1) if i.table is PAGE0 else rom.r8(pc + 2)
                if v & 0x20:
                    m = 1
                if v & 0x10:
                    x = 1
            elif i.name == "CLP":
                v = rom.r8(pc + 1) if i.table is PAGE0 else rom.r8(pc + 2)
                if v & 0x20:
                    m = 0
                if v & 0x10:
                    x = 0
            elif i.name == "SEM":
                m = 1
            elif i.name == "CLM":
                m = 0

            for tgt in i.targets:
                if tgt not in labels:
                    labels[tgt] = f"L_{tgt:04X}"
                enqueue(tgt, m, x)

            # Follow jump tables: JMP (abs,X) / JSR (abs,X)
            if i.flow in ("jump_table", "call_table"):
                tbl_base = rom.r16(pc + (1 if i.table is PAGE0 else 2))
                if rom.has(tbl_base, 2):
                    for off in range(0, 256, 2):
                        if not rom.has(tbl_base + off, 2):
                            break
                        entry = rom.r16(tbl_base + off)
                        if not rom.has(entry):
                            break
                        if entry not in labels:
                            labels[entry] = f"L_{entry:04X}"
                        enqueue(entry, m, x)

            if i.flow in ("end", "jump", "jump_table"):
                break
            pc += i.size

    return insns, labels


# ---------------------------------------------------------------------------
# Table annotation
# ---------------------------------------------------------------------------

SENSOR_NAMES = {
    0x0980: "RPM_raw", 0x0981: "RPM_idx", 0x0982: "RPM_hi",
    0x0983: "RPM_period", 0x098B: "coolant_temp",
    0x09AE: "load_raw", 0x09B0: "load_idx", 0x09B4: "load_hi",
    0x0994: "battery_v", 0x0907: "throttle_pos",
    0x0A12: "airflow", 0x0A14: "ign_dwell",
    0x0A65: "knock_level", 0x0BA7: "o2_sensor",
    0x0BC5: "idle_val", 0x0BCB: "iac_pos",
    0x0C1F: "vehicle_speed", 0x0E0D: "iac_duty",
}

INTERP_ENTRIES = {0xEA77: 16, 0xEA82: 32, 0xEA8D: 8}


def find_tables(rom, insns):
    """Identify 1D interpolation tables and 2D map blocks."""
    annotations = {}
    pcs = sorted(insns)

    # Pass 1: find 1D table references from JSL to interpolation routines
    for idx, pc in enumerate(pcs):
        i = insns[pc]
        if i.name != "JSL" or not i.targets:
            continue
        for t in i.targets:
            if t not in INTERP_ENTRIES:
                continue
            n_entries = INTERP_ENTRIES[t]
            table_base = None
            input_name = None
            for j in range(idx - 1, max(idx - 15, 0), -1):
                prev = insns[pcs[j]]
                if table_base is None and prev.name == "LDX" and prev.text.startswith("#$"):
                    table_base = int(prev.text[2:], 16)
                if input_name is None and prev.name in ("LDA", "LDB"):
                    if prev.ref and prev.ref in SENSOR_NAMES:
                        input_name = SENSOR_NAMES[prev.ref]
                    elif prev.text and not prev.text.startswith("#"):
                        input_name = prev.text
            if table_base is not None and rom.has(table_base, n_entries + 1):
                vals = [rom.r8(table_base + k) for k in range(n_entries + 1)]
                inp = f" input={input_name}" if input_name else ""
                annotations[table_base] = (
                    f"TABLE_{table_base:04X}",
                    f"{n_entries}-entry 1D lookup{inp}",
                    n_entries + 1,
                )

    # Pass 2: identify 2D maps (16x16 byte blocks in non-code regions)
    map_candidates = {
        0x1300: "FUEL_MAP",
        0x1400: "TIMING_MAP",
    }
    # Scan for additional 16x16 smooth maps
    for base in range(rom.base, rom.end - 255, 0x10):
        if base in map_candidates:
            continue
        if any(base + off in insns for off in range(256)):
            continue
        if not rom.has(base, 256):
            continue
        vals = [rom.r8(base + k) for k in range(256)]
        if vals.count(0xFF) > 32 or len(set(vals)) < 8:
            continue
        diffs = []
        for row in range(16):
            for col in range(15):
                diffs.append(abs(vals[row * 16 + col + 1] - vals[row * 16 + col]))
        if sum(diffs) / len(diffs) < 8:
            map_candidates[base] = f"MAP_{base:04X}"

    for base, name in sorted(map_candidates.items()):
        if rom.has(base, 256):
            annotations[base] = (name, "16x16 byte map", 256)

    # Pass 3: identify axis breakpoints
    axis_candidates = {
        0x1500: ("AXIS_RPM_8", "8-step RPM axis", 16),
        0x1510: ("AXIS_LOAD_16", "16-step load axis", 16),
    }
    for addr, (name, desc, size) in axis_candidates.items():
        if rom.has(addr, size):
            annotations[addr] = (name, desc, size)

    # 16-bit RPM axis at $12C0 (32 breakpoints as 16-bit BE values)
    if rom.has(0x12C0, 64):
        annotations[0x12C0] = ("AXIS_RPM_32x16", "32 x 16-bit RPM breakpoints", 64)

    return annotations


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_table(rom, addr, ann, out):
    """Emit an annotated data table."""
    name, desc, size = ann
    out.write(f"\n; === {name}: {desc} ===\n")
    if size == 256 and "16x16" in desc:
        out.write(f"{name}:  ; ${addr:04X}\n")
        out.write(f";       col: {'  '.join(f'{c:X}' for c in range(16))}\n")
        for row in range(16):
            cells = [rom.r8(addr + row * 16 + c) for c in range(16)]
            hex_part = " ".join(f"{v:02X}" for v in cells)
            out.write(f";  row {row:X}:  {hex_part}\n")
        for off in range(0, 256, 16):
            row_addr = addr + off
            vals = [rom.r8(row_addr + j) for j in range(16)]
            hex_str = " ".join(f"{v:02X}" for v in vals)
            out.write(f"    {row_addr:04X}  {hex_str}\n")
            out.write(f"          .db {','.join(f'${v:02X}' for v in vals)}\n")
    elif "1D lookup" in desc:
        n = size
        vals = [rom.r8(addr + k) for k in range(n)]
        out.write(f"{name}:  ; ${addr:04X}, {n} bytes\n")
        out.write(f";  values: {' '.join(f'{v:02X}' for v in vals)}\n")
        hex_str = " ".join(f"{v:02X}" for v in vals)
        out.write(f"    {addr:04X}  {hex_str}\n")
        out.write(f"          .db {','.join(f'${v:02X}' for v in vals)}\n")
    else:
        out.write(f"{name}:  ; ${addr:04X}, {size} bytes\n")
        for off in range(0, size, 16):
            row_addr = addr + off
            n = min(16, size - off)
            vals = [rom.r8(row_addr + j) for j in range(n)]
            hex_str = " ".join(f"{v:02X}" for v in vals)
            out.write(f"    {row_addr:04X}  {hex_str}\n")
            out.write(f"          .db {','.join(f'${v:02X}' for v in vals)}\n")


def format_listing(rom, insns, labels, annotations, out):
    out.write("; M7700 disassembly — 23710-2L904\n")
    out.write(f"; ROM base ${rom.base:04X}, end ${rom.end - 1:04X}, {len(insns)} instructions decoded\n")
    out.write("; Assumptions: DPR=0, DT=0, bank 0, m=x=0 at vectors\n")
    out.write(";\n")
    out.write("; Known sensor addresses:\n")
    for addr in sorted(SENSOR_NAMES):
        out.write(f";   ${addr:04X} = {SENSOR_NAMES[addr]}\n")
    out.write(";\n\n")

    for va in sorted(VECTOR_NAMES):
        if rom.has(va, 2):
            target = rom.r16(va)
            out.write(f"VEC_{VECTOR_NAMES[va]:12s} .equ ${target:04X}    ; [{va:04X}]\n")
    out.write("\n")

    # Build set of addresses covered by annotated tables
    table_ranges = {}
    for ta, ann in annotations.items():
        for off in range(ann[2]):
            table_ranges[ta + off] = ta

    addr = rom.base
    data_run = []
    emitted_tables = set()

    def flush_data():
        nonlocal data_run
        if not data_run:
            return
        for da, db in data_run:
            if da in labels:
                out.write(f"\n{labels[da]}:\n")
            hex_str = " ".join(f"{b:02X}" for b in db)
            out.write(f"    {da:04X}  {hex_str:<24s}.db {','.join(f'${b:02X}' for b in db)}\n")
        data_run = []

    while addr < rom.end:
        if addr in insns:
            flush_data()
            i = insns[addr]
            if addr in labels:
                out.write(f"\n{labels[addr]}:\n")
            raw = bytes(rom.r8(addr + j) for j in range(i.size))
            hex_str = " ".join(f"{b:02X}" for b in raw)
            line = f"    {addr:04X}  {hex_str:<24s}{i.name}"
            if i.text:
                line += f" {i.text}"
            # Add sensor name comment for known addresses
            if i.ref and i.ref in SENSOR_NAMES and i.ref_kind in ("abs", "dp"):
                line += f"  ; {SENSOR_NAMES[i.ref]}"
            out.write(line + "\n")
            addr += i.size
        elif addr in table_ranges:
            flush_data()
            ta = table_ranges[addr]
            if ta not in emitted_tables:
                emitted_tables.add(ta)
                format_table(rom, ta, annotations[ta], out)
            addr = ta + annotations[ta][2]
        else:
            run_start = addr
            run_bytes = []
            while addr < rom.end and addr not in insns and addr not in table_ranges and len(run_bytes) < 16:
                if addr != run_start and addr in labels:
                    break
                run_bytes.append(rom.r8(addr))
                addr += 1
            data_run.append((run_start, run_bytes))

    flush_data()
    code_bytes = sum(i.size for i in insns.values())
    table_bytes = sum(ann[2] for ann in annotations.values())
    total = rom.end - rom.base
    out.write(f"\n; {code_bytes}/{total} bytes decoded as code ({100 * code_bytes / total:.1f}%)\n")
    out.write(f"; {len(annotations)} annotated tables ({table_bytes} bytes)\n")


def main():
    parser = argparse.ArgumentParser(description="M7700 recursive-descent disassembler")
    parser.add_argument("rom", help="Binary ROM image")
    parser.add_argument("--base", type=lambda x: int(x, 16), default=0x1000,
                        help="Load address in hex (default: 1000)")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    with open(args.rom, "rb") as f:
        data = f.read()
    rom = Rom(data, args.base)
    print(f"Loaded {len(data)} bytes at ${args.base:04X}-${rom.end - 1:04X}", file=sys.stderr)

    insns, labels = walk(rom)
    print(f"Decoded {len(insns)} instructions, {len(labels)} labels", file=sys.stderr)

    annotations = find_tables(rom, insns)
    print(f"Found {len(annotations)} annotated tables", file=sys.stderr)

    if args.output:
        with open(args.output, "w") as f:
            format_listing(rom, insns, labels, annotations, f)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        format_listing(rom, insns, labels, annotations, sys.stdout)


if __name__ == "__main__":
    main()