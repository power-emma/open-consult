#!/usr/bin/env python3
"""Bounded laptop fuel-percentage control with simultaneous ECU telemetry.

Uses native Consult test 81, not the RAM overrun. Default is offline preview.
Live test: python3 tools/fuel_control_test.py --percents 100,103,100 --run
The engine must be running to verify both fuel-feedback banks. STOP removes
the temporary active-test flags. This does not change ROM calibration maps.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from consult.experimental import require_research_ecu
from consult.protocol import Consult, ConsultError
from consult.transport import DEFAULT_DEV, Transport
from c9_direct_sweep import read_checked

# All local RAM: none falls in the second-processor forwarding window.
ADDRESSES = (0x0995, 0x0994, 0x0ABE, 0x0ABD, 0x0730, 0x0731,
             0x0DAA, 0x0DA9, 0x0DAC, 0x0DAB, 0x07B7, 0x0770, 0x098B)


def parse_percents(text):
    result = [int(part.strip()) for part in text.split(',')]
    if not result or any(not 75 <= percent <= 125 for percent in result):
        raise ValueError('percentages must be decimal integers in 75..125')
    return result


def build_command(percent):
    if not 75 <= percent <= 125:
        raise ValueError('percentage outside the ROM clamp 75..125')
    # Test first, then local C9 list: final parser mode is C9, while F0 also
    # commits the pending test flags. 13 reads + 2 test args = 28 arg bytes.
    return bytes((0x0A, 0x81, percent)) + b''.join(
        bytes((0xC9, address >> 8, address & 255)) for address in ADDRESSES)


def decode_sample(data, percent):
    if len(data) != len(ADDRESSES):
        raise ConsultError(f'expected {len(ADDRESSES)} telemetry bytes, got {len(data)}')
    word = lambda index: (data[index] << 8) | data[index + 1]
    sample = {
        'rpm': word(0) * 12.5, 'load_code': word(2),
        'alpha_a': data[4], 'alpha_b': data[5],
        'injector_a_ms': word(6) / 100, 'injector_b_ms': word(8) / 100,
        'active_flags': data[10], 'test_value': data[11], 'speed_kmh': data[12] * 2,
    }
    sample['override_matches'] = bool(data[10] & 0x02) and data[11] == percent
    sample['both_banks_match'] = sample['override_matches'] and data[4] == data[5] == percent
    return sample


def run_step(client, percent, seconds, result, *, clock=time.monotonic):
    baseline = read_checked(client, [0x0995, 0x0994, 0x0730, 0x0731])
    result.update(percent=percent, baseline=list(baseline), samples=[], command_hex=build_command(percent).hex(' '))
    if int.from_bytes(baseline[:2], 'big') == 0:
        raise ConsultError('engine is not running; fuel-control request not sent')
    primary = cleanup = None
    try:
        result['request_attempted'] = True
        client.command(build_command(percent), retries=0, mutation=True)
        started = clock()
        while clock() - started < seconds:
            # Finish the last frame rather than imposing a shortened timeout
            # halfway through its serial payload at the hold-time boundary.
            data = client.read_frame(expected_len=len(ADDRESSES), timeout=1.0)
            sample = decode_sample(data, percent)
            sample['elapsed_seconds'] = round(clock() - started, 4)
            result['samples'].append(sample)
    except BaseException as error:
        primary = error
    finally:
        try:
            ack, _ = client.stop(timeout=0.5)
            if ack is None:
                cleanup = ConsultError('active-test stop acknowledgment missing')
            else:
                result['stop_acknowledged'] = True
        except BaseException as error:
            cleanup = error
    if primary is not None or cleanup is not None:
        if isinstance(primary, (KeyboardInterrupt, SystemExit)):
            raise primary
        raise ConsultError(f'fuel test incomplete: primary={primary!r}; cleanup={cleanup!r}') from primary
    # Require repeated applied-bank values, not merely an echoed request or
    # a single transient sample. Early settling samples remain in the report.
    tail = result['samples'][-3:]
    result['both_banks_verified'] = len(tail) == 3 and all(s['both_banks_match'] for s in tail)
    flags = read_checked(client, [0x07B7])[0]
    result['active_flags_after_stop'] = flags
    result['override_released'] = not bool(flags & 0x02)
    result['status'] = ('verified' if result['both_banks_verified'] and result['override_released']
                        else 'not_verified')
    return result['status'] == 'verified'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--percents', default='100,103,100', help='decimal percentages, default 100,103,100')
    parser.add_argument('--seconds', type=float, default=2.0, help='hold time per step, 0.2..60 (default 2)')
    parser.add_argument('--dev', default=DEFAULT_DEV)
    parser.add_argument('--run', action='store_true', help='run bounded native fuel-control test with engine running')
    parser.add_argument('--output', type=Path, help='fresh JSON report path; raw log shares its stem')
    args = parser.parse_args()
    try:
        percents = parse_percents(args.percents)
        if not 0.2 <= args.seconds <= 60:
            raise ValueError('hold time must be in 0.2..60 seconds')
    except ValueError as error:
        parser.error(str(error))
    print(f'Native fuel test 81: {percents} percent, {args.seconds:g}s per step.')
    print('ROM clamp: 75..125%; temporary feedback override, not a permanent fuel-map edit.')
    if not args.run:
        print('Offline preview only; no serial device opened.')
        print('First command:', build_command(percents[0]).hex(' '))
        return 0
    output = args.output or ROOT / 'logs' / (datetime.now().strftime('%Y-%m-%d_%H%M%S_%f') + '_fuel-control.json')
    raw_log = output.with_suffix('.log')
    if output == raw_log or output.exists() or raw_log.exists():
        parser.error('choose a fresh report filename')
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'status': 'starting', 'percents': percents, 'seconds_per_step': args.seconds,
              'mechanism': 'native 0A 81 plus local C9 telemetry', 'steps': []}
    transport = None
    code = 2
    try:
        transport = Transport(args.dev, str(raw_log))
        client = Consult(transport)
        if client.init(ecu=0xED) is None:
            raise ConsultError('engine initialization failed')
        require_research_ecu(client)
        for percent in percents:
            step = {'request_attempted': False}
            report['steps'].append(step)
            verified = run_step(client, percent, args.seconds, step)
            output.write_text(json.dumps(report, indent=2) + '\n')
            last = step['samples'][-1] if step['samples'] else {}
            print(f"{percent}%: {step['status']}; alpha={last.get('alpha_a')}/{last.get('alpha_b')}; "
                  f"injectors={last.get('injector_a_ms')}/{last.get('injector_b_ms')} ms; "
                  f"released={step['override_released']}")
            if not verified:
                report['status'] = 'stopped_on_unverified_step'
                code = 1
                break
        else:
            report['status'] = 'completed'
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
