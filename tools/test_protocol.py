#!/usr/bin/env python3
"""Offline framework runner. Strict mode rejects known gaps and skipped tests."""
import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-conformance", action="store_true",
                        help="fail on known gaps or skips, as well as regressions")
    parser.add_argument("--report", type=Path, help="write a JSON summary")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "schema_version": 1,
        "scope": "offline_protocol_and_posix_io",
        "hardware_validated": False,
        "tests_run": result.testsRun,
        "known_gaps": [test.id() for test, _ in result.expectedFailures],
        "skipped": [{"test": test.id(), "reason": reason}
                    for test, reason in result.skipped],
        "failures": [test.id() for test, _ in result.failures],
        "errors": [test.id() for test, _ in result.errors],
        "unexpected_successes": [test.id() for test in result.unexpectedSuccesses],
    }
    report["offline_conformance"] = bool(
        result.wasSuccessful() and not result.expectedFailures and not result.skipped
    )
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if (result.wasSuccessful() and
                 (not args.require_conformance or report["offline_conformance"])) else 1


if __name__ == "__main__":
    sys.exit(main())
