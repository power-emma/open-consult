#!/usr/bin/env python3
"""Capture ignition timing and internal terms, optionally testing native 82.

Offline preview is default. Parameter bytes are RAW HEX: their signedness,
units and advance/retard direction are not established for this firmware.

  python3 tools/timing_control_probe.py --raw-values 00,01,00
  python3 tools/timing_control_probe.py --run                    # passive only
  python3 tools/timing_control_probe.py --raw-values 00,01,00 --run

Live capture requires the engine running. Each active step is bracketed by
normal-control captures. STOP and override release are checked. No ROM writes.
"""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from consult.experimental import require_research_ecu
from consult.protocol import Consult, ConsultError
from consult.transport import DEFAULT_DEV, Transport
from c9_direct_sweep import read_checked

# 19 local C9 addresses, plus two active-test arguments = 40 wire argument bytes.
ADDRESSES = (0x0995, 0x0994, 0x0732, 0x0771, 0x07B7, 0x0BA6, 0x0BA8, 0x0BA9,
             0x0E01, 0x096D, 0x0DB0, 0x0DB1, 0x0DB2, 0x0DB3, 0x0DB4, 0x0DB5,
             0x0DB8, 0x0ABE, 0x0ABD)


def build_command(raw=None):
    if raw is not None and (not isinstance(raw, int) or isinstance(raw, bool) or not 0 <= raw <= 255):
        raise ValueError('timing parameter must be a raw hex byte 00..FF')
    prefix = b'' if raw is None else bytes([0x0A, 0x82, raw])
    return prefix + b''.join(bytes([0xC9, address >> 8, address & 255]) for address in ADDRESSES)


def decode_sample(data, raw):
    if len(data) != len(ADDRESSES):
        raise ConsultError('short timing telemetry')
    active = bool(data[4] & 4)
    return {
        'rpm': ((data[0] << 8) | data[1]) * 12.5,
        'reported_btdc': 110 - data[2], 'reported_code': data[2],
        'parameter_byte': data[3], 'active_flags': data[4],
        'base_code': data[5], 'target_code': data[6], 'output_code': data[7],
        'correction_code': data[8], 'rpm_correction_code': data[9],
        'cylinder_trim_codes': list(data[10:16]), 'knock_code': data[16],
        'load_code': (data[17] << 8) | data[18],
        'request_state_matches': not active if raw is None else active and data[3] == raw,
    }


def capture_stage(client, raw, seconds, result, *, clock=time.monotonic):
    result.update(raw_parameter=raw, kind='normal_control' if raw is None else 'native_82', samples=[])
    baseline = read_checked(client, [0x0995, 0x0994])
    if int.from_bytes(baseline, 'big') == 0:
        raise ConsultError('engine is not running; timing request not sent')
    primary = cleanup = None
    try:
        result['request_attempted'] = True
        client.command(build_command(raw), retries=0, mutation=raw is not None)
        started = clock()
        while clock() - started < seconds:
            sample = decode_sample(client.read_frame(expected_len=len(ADDRESSES), timeout=1.0), raw)
            sample['elapsed_seconds'] = round(clock() - started, 4)
            result['samples'].append(sample)
            if sample['rpm'] == 0:
                raise ConsultError('engine stopped during timing capture')
    except BaseException as error:
        primary = error
    finally:
        try:
            ack, _ = client.stop(timeout=0.5)
            if ack is None:
                cleanup = ConsultError('timing capture stop acknowledgment missing')
            else:
                result['stop_acknowledged'] = True
        except BaseException as error:
            cleanup = error
    if primary is not None or cleanup is not None:
        if isinstance(primary, (KeyboardInterrupt, SystemExit)):
            raise primary
        raise ConsultError(f'timing capture incomplete: primary={primary!r}; cleanup={cleanup!r}') from primary
    flags = read_checked(client, [0x07B7])[0]
    result['active_flags_after_stop'] = flags
    result['override_released'] = not bool(flags & 4)
    tail = result['samples'][-3:]
    result['request_state_verified'] = len(tail) == 3 and all(s['request_state_matches'] for s in tail)
    if not result['request_state_verified'] or not result['override_released']:
        raise ConsultError('timing request/normal-control state or override release not verified')
    samples = result['samples']
    result['reported_timing_summary'] = {
        'median_btdc': statistics.median(s['reported_btdc'] for s in samples),
        'min_btdc': min(s['reported_btdc'] for s in samples),
        'max_btdc': max(s['reported_btdc'] for s in samples),
        'min_rpm': min(s['rpm'] for s in samples), 'max_rpm': max(s['rpm'] for s in samples),
        'min_load_code': min(s['load_code'] for s in samples),
        'max_load_code': max(s['load_code'] for s in samples),
    }
    # State application is observable; physical spark angle, parameter units
    # and causation of a timing change need separate calibration evidence.
    result['timing_parameter_semantics_verified'] = False
    result['status'] = 'captured'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--raw-values', help='optional hex parameter list; omitted means passive capture only')
    parser.add_argument('--seconds', type=float, default=2.0, help='seconds per capture stage, default 2')
    parser.add_argument('--run', action='store_true', help='live capture; engine running')
    parser.add_argument('--dev', default=DEFAULT_DEV)
    parser.add_argument('--output', type=Path, help='fresh JSON report path; raw log shares stem')
    args = parser.parse_args()
    try:
        values = [] if args.raw_values is None else [int(part.strip(), 16) for part in args.raw_values.split(',')]
        if not math.isfinite(args.seconds) or not 0.2 <= args.seconds <= 30:
            raise ValueError('capture duration must be finite and in 0.2..30 seconds')
        for raw in values:
            build_command(raw)
    except ValueError as error:
        parser.error(str(error))
    stages = [None]
    for raw in values:
        stages.extend([raw, None])
    print('Capture order:', ' -> '.join('normal' if raw is None else f'raw ${raw:02X}' for raw in stages))
    print('RAW parameter semantics unverified; reported BTDC is ECU telemetry, not a timing-light measurement.')
    if not args.run:
        print('Offline preview only; no serial connection.')
        return 0
    output = args.output or ROOT / 'logs' / (datetime.now().strftime('%Y-%m-%d_%H%M%S_%f') + '_timing-control.json')
    raw_log = output.with_suffix('.log')
    if output == raw_log or output.exists() or raw_log.exists():
        parser.error('choose fresh report and raw-log paths')
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'status': 'starting', 'raw_values': values, 'stages': [],
              'timing_parameter_semantics_verified': False}
    transport = None
    code = 2
    try:
        transport = Transport(args.dev, str(raw_log))
        client = Consult(transport)
        if client.init(ecu=0xED) is None:
            raise ConsultError('engine initialization failed')
        require_research_ecu(client)
        preceding = None
        for raw in stages:
            result = {'request_attempted': False}
            report['stages'].append(result)
            capture_stage(client, raw, args.seconds, result)
            summary = result['reported_timing_summary']
            if raw is not None and preceding is not None:
                result['median_reported_delta_from_preceding_normal'] = summary['median_btdc'] - preceding
            if raw is None:
                preceding = summary['median_btdc']
            output.write_text(json.dumps(report, indent=2) + '\n')
            label = 'normal' if raw is None else f'raw ${raw:02X}'
            print(f"{label}: reported median={summary['median_btdc']} BTDC, "
                  f"range={summary['min_btdc']}..{summary['max_btdc']}, "
                  f"RPM={summary['min_rpm']}..{summary['max_rpm']}; released={result['override_released']}")
        report['status'] = 'captured_semantics_unclassified'
        code = 0
    except (OSError, ValueError, ConsultError, KeyboardInterrupt) as error:
        report['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'unverified'
        report['error'] = f'{type(error).__name__}: {error}'
        print(report['error'], file=sys.stderr)
        code = 130 if isinstance(error, KeyboardInterrupt) else 2
    finally:
        try:
            if transport is not None:
                transport.close()
        finally:
            output.write_text(json.dumps(report, indent=2) + '\n')
            print(f'Report: {output}\nRaw log: {raw_log}')
    return code


if __name__ == '__main__':
    sys.exit(main())
