#!/usr/bin/env python3
"""Preview or test a direct request-builder RAM write on ECU 23710-2L904.

Examples (key on, engine off for a live trial):
  python3 write-access/tools/c9_direct_test.py --value 42
  python3 write-access/tools/c9_direct_test.py --value 42 --run --dev /dev/ttyUSB0

Default is offline. The live path sends one mutation request, requests one
frame, requires stop acknowledgment, then reads RAM independently. Receiving
one frame does not guarantee exactly one ECU-side frame was built.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from consult.experimental import mutation_stream, require_research_ecu
from consult.protocol import Consult, ConsultError
from consult.transport import DEFAULT_DEV, Transport
from trace_ram_write import HiddenRoutine, direct_payload


class AlreadyMatches(ConsultError):
    """A baseline already has the requested byte; no write was attempted."""


def plan_test(target, value):
    addresses = direct_payload(target, value)
    model = HiddenRoutine(addresses).run()
    if model.mem[target] != value or model.mem[target + 1] != 0x0E:
        raise ValueError('control-state alias changes this candidate; choose another target')
    command = b''.join(bytes((0xC9, addr >> 8, addr & 255)) for addr in addresses)
    touched = sorted({a for event in model.stores
                      for a in range(event.address, event.address + event.width)})
    return {
        'target': target, 'value': value, 'companion_address': target + 1,
        'companion_value': 0x0E, 'addresses': addresses, 'command_hex': command.hex(' '),
        'model_touched_addresses': touched,
        'modeled_final_bytes': {f'{a:04X}': model.mem[a] for a in touched},
        'model_scope': 'return from $543F; background tasks and interrupts excluded',
    }


def snapshot(client, addresses):
    result = {}
    for start in range(0, len(addresses), 8):
        chunk = addresses[start:start + 8]
        data = client.read_memory(chunk)
        if len(data) != len(chunk):
            raise ConsultError('short RAM snapshot')
        result.update({f'{addr:04X}': byte for addr, byte in zip(chunk, data)})
    return result


def run_trial(client, plan, report):
    if client.init(ecu=0xED) is None:
        raise ConsultError('engine initialization failed')
    require_research_ecu(client)
    report['identity'] = '23710-2L904'
    # Capture all modeled write destinations and both target bytes.
    watch = sorted(set(plan['model_touched_addresses']) |
                   {plan['target'], plan['companion_address']})
    report['before'] = snapshot(client, watch)
    if report['before'][f"{plan['target']:04X}"] == plan['value']:
        raise AlreadyMatches('target already equals requested value; no mutation sent; choose a different value')
    rpm_bytes = client.read_memory([0x0995, 0x0994])
    if len(rpm_bytes) != 2:
        raise ConsultError('short RPM read; no mutation sent')
    report['rpm_before'] = int.from_bytes(rpm_bytes, 'big') * 12.5
    if report['rpm_before'] != 0:
        raise ConsultError('engine is running; this test requires engine off; no mutation sent')

    report['mutation_attempted'] = True
    frames = mutation_stream(client, bytes.fromhex(plan['command_hex']),
                             frames=1, expected_len=len(plan['addresses']))
    report['frames_hex'] = [frame.hex(' ') for frame in frames]
    report['stop_acknowledged'] = True
    # A frame payload is not a readback of the chosen destination. Reinitialize
    # and take independent local C9 reads after the mutation stream has stopped.
    if client.init(ecu=0xED) is None:
        raise ConsultError('post-test initialization failed; write remains unverified')
    report['after'] = snapshot(client, watch)
    report['verification'] = snapshot(client, [plan['target'], plan['companion_address']])
    target_key, companion_key = f"{plan['target']:04X}", f"{plan['companion_address']:04X}"
    wanted = {target_key: plan['value'], companion_key: plan['companion_value']}
    report['readback_matches'] = all(
        report[phase][key] == byte for phase in ('after', 'verification')
        for key, byte in wanted.items())
    report['observed_changes'] = {
        key: {'before': report['before'][key], 'after': byte}
        for key, byte in report['after'].items() if byte != report['before'][key]
    }
    report['status'] = 'readback_matches' if report['readback_matches'] else 'readback_mismatch'
    return report['readback_matches']


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--target', type=lambda s: int(s, 16), default=0x0817,
                        help='hex RAM address; default 0817')
    parser.add_argument('--value', type=lambda s: int(s, 16), default=0x42,
                        help='hex byte; default 42')
    parser.add_argument('--dev', default=DEFAULT_DEV)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true', help='execute one live trial')
    mode.add_argument('--dry-run', action='store_true', help='offline preview (default)')
    parser.add_argument('--output', type=Path, help='JSON report path; live raw log uses the same stem')
    args = parser.parse_args()
    try:
        plan = plan_test(args.target, args.value)
    except ValueError as error:
        parser.error(str(error))
    print(f"Target ${args.target:04X} <- ${args.value:02X}; companion ${args.target+1:04X} <- $0E")
    print('Other modeled RAM stores:', ' '.join(f'{a:04X}' for a in plan['model_touched_addresses']
                                             if a not in (args.target, args.target + 1)))
    print('C9 addresses:', ' '.join(f'{a:04X}' for a in plan['addresses']))
    report = {'plan': plan, 'mutation_attempted': False, 'status': 'offline_preview'}
    if not args.run:
        print('Offline preview only. Use --run for one ECU trial, key on / engine off.')
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n')
        return 0

    output = args.output or ROOT / 'logs' / (datetime.now().strftime('%Y-%m-%d_%H%M%S_%f') + '_direct-write.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_log = output.with_suffix('.log')
    if output.exists() or raw_log.exists():
        parser.error('report or raw log already exists; choose a new output path')
    print(f'One live trial on {args.dev}; raw log: {raw_log}')
    transport = None
    exit_code = 2
    try:
        transport = Transport(args.dev, str(raw_log))
        transport.note(f'direct write trial target=${args.target:04X} value=${args.value:02X}')
        matched = run_trial(Consult(transport), plan, report)
        exit_code = 0 if matched else 1
        print('Independent readbacks MATCH.' if matched else 'Independent readbacks DO NOT MATCH.')
        for key, change in report['observed_changes'].items():
            print(f"  ${key}: ${change['before']:02X} -> ${change['after']:02X}")
    except (OSError, ValueError, ConsultError, KeyboardInterrupt) as error:
        report['status'] = 'unverified' if report['mutation_attempted'] else 'not_attempted'
        report['error'] = f'{type(error).__name__}: {error}'
        print(report['error'], file=sys.stderr)
        exit_code = 130 if isinstance(error, KeyboardInterrupt) else 2
    finally:
        try:
            if transport is not None:
                transport.close()
        finally:
            output.write_text(json.dumps(report, indent=2) + '\n')
            print(f'Report: {output}')
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
