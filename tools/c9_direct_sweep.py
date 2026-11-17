#!/usr/bin/env python3
"""Sweep caller-selected bytes at one RAM address during a single key-on.

  python3 tools/c9_direct_sweep.py                       # offline preview
  python3 tools/c9_direct_sweep.py --run --dev /dev/ttyUSB0
  python3 tools/c9_direct_sweep.py --values FF,00,21,67 --run
  python3 tools/c9_direct_sweep.py --addresses 0810-0822 --value 67 --run

Fast mode (default) verifies identity once and keeps the initialized session.
Each trial checks baseline/RPM together and independently reads the target pair
twice after an acknowledged stop. --full-checks restores full snapshots and
reinitialization per trial. No power cycle, mutation retries or restore.
"""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from c9_direct_test import AlreadyMatches, plan_test, run_trial
from consult.experimental import mutation_stream, require_research_ecu
from consult.protocol import Consult, ConsultError
from consult.transport import DEFAULT_DEV, Transport


def parse_ranges(text, limit=255):
    values = []
    for item in text.split(','):
        parts = item.strip().split('-')
        if len(parts) == 1:
            values.append(int(parts[0], 16))
        elif len(parts) == 2:
            first, last = (int(part, 16) for part in parts)
            if not 0 <= first <= limit or not 0 <= last <= limit:
                raise ValueError(f'hex values must be in 0..{limit:X}')
            values.extend(range(first, last + (1 if last >= first else -1),
                                1 if last >= first else -1))
        else:
            raise ValueError('use comma-separated hex bytes or ranges, e.g. 00-FF or FF,00,21,67')
    if not values or any(not 0 <= value <= limit for value in values):
        raise ValueError(f'hex values must be in 0..{limit:X}')
    return values


def parse_values(text):
    values = parse_ranges(text)
    if any(a == b for a, b in zip(values, values[1:])):
        raise ValueError('adjacent identical values would not demonstrate a change')
    return values


def address_plans(addresses, value):
    if not 0 <= value <= 255:
        raise ValueError('chosen value must be a hex byte in 00..FF')
    if len(set(addresses)) != len(addresses):
        raise ValueError('address sweep requires unique addresses')
    plans, unsupported = [], []
    for address in addresses:
        try:
            plans.append(plan_test(address, value))
        except ValueError as error:
            unsupported.append({'target': address, 'reason': str(error)})
    if not plans:
        raise ValueError('no requested address passes the direct-write model')
    return plans, unsupported


def read_checked(client, addresses):
    """Read once and require an acknowledged stop before reusing the session."""
    payload = b''.join(bytes((0xC9, addr >> 8, addr & 255)) for addr in addresses)
    primary = cleanup = None
    data = None
    try:
        client.command(payload, retries=0)
        data = client.read_frame(expected_len=len(addresses), timeout=1.0)
        if len(data) != len(addresses):
            raise ConsultError('short sweep readback')
    except BaseException as error:
        primary = error
    finally:
        try:
            ack, _ = client.stop(timeout=0.5)
            if ack is None:
                cleanup = ConsultError('readback stop acknowledgment missing')
        except BaseException as error:
            cleanup = error
    if primary is not None or cleanup is not None:
        if isinstance(primary, (KeyboardInterrupt, SystemExit)):
            raise primary
        raise ConsultError(f'readback failed: primary={primary!r}; cleanup={cleanup!r}') from primary
    return data


def run_fast_trial(client, plan, report):
    """Use the already initialized wire session with a fresh verified baseline."""
    client.ecu = 0xED
    target, companion = plan['target'], plan['companion_address']
    report['identity'] = '23710-2L904 (checked at sweep start)'
    report['verification_scope'] = 'target and companion; collateral snapshots omitted'
    data = read_checked(client, [target, companion, 0x0995, 0x0994])
    keys = [f'{target:04X}', f'{companion:04X}']
    report['before'] = dict(zip(keys, data[:2]))
    report['rpm_before'] = int.from_bytes(data[2:], 'big') * 12.5
    if report['rpm_before'] != 0:
        raise ConsultError('engine is running; no mutation sent')
    if data[0] == plan['value']:
        raise AlreadyMatches('target already equals requested value; no mutation sent')
    report['mutation_attempted'] = True
    frames = mutation_stream(client, bytes.fromhex(plan['command_hex']),
                             frames=1, expected_len=len(plan['addresses']))
    report['frames_hex'] = [frame.hex(' ') for frame in frames]
    report['stop_acknowledged'] = True
    for phase in ('after', 'verification'):
        report[phase] = dict(zip(keys, read_checked(client, [target, companion])))
    wanted = {keys[0]: plan['value'], keys[1]: plan['companion_value']}
    report['readback_matches'] = all(report[phase] == wanted for phase in ('after', 'verification'))
    report['observed_changes'] = {
        key: {'before': report['before'][key], 'after': byte}
        for key, byte in report['after'].items() if byte != report['before'][key]
    }
    report['status'] = 'readback_matches' if report['readback_matches'] else 'readback_mismatch'
    return report['readback_matches']


def describe_checks(trial):
    """Separate target failure from companion failure without changing pass criteria."""
    key, companion = f"{trial['target']:04X}", f"{trial['target']+1:04X}"
    phases = ('after', 'verification')
    if not all(phase in trial for phase in phases):
        return
    trial['target_readbacks_match'] = all(trial[phase].get(key) == trial['value'] for phase in phases)
    trial['companion_readbacks_match'] = all(trial[phase].get(companion) == 0x0E for phase in phases)
    trial['mismatch_details'] = [
        {'phase': phase, 'address': address, 'expected': expected,
         'actual': trial[phase].get(address)}
        for phase in phases for address, expected in ((key, trial['value']), (companion, 0x0E))
        if trial[phase].get(address) != expected
    ]


def outcome_text(trial):
    key, companion = f"{trial['target']:04X}", f"{trial['target']+1:04X}"

    def cell(phase, address):
        value = trial.get(phase, {}).get(address)
        return '??' if value is None else f'{value:02X}'

    if trial['status'] == 'already_matches':
        return f"baseline={cell('before', key)} already_matches (no write)"
    text = f"readback={cell('verification', key)} companion={cell('verification', companion)} {trial['status']}"
    if trial['status'] == 'readback_mismatch':
        text += (f" first={cell('after', key)}/{cell('after', companion)}"
                 f" second={cell('verification', key)}/{cell('verification', companion)}"
                 f" expected={trial['value']:02X}/0E")
    return text


def run_sweep(client_factory, plans, report, on_result, *, fast=True,
              address_mode=False, continue_on_mismatch=False):
    """Run one sweep; checkpoint every outcome and stop at the first problem."""
    started = time.monotonic()
    initial = client_factory()
    if initial.init(ecu=0xED) is None:
        raise ConsultError('initial engine handshake failed')
    require_research_ecu(initial)
    data = read_checked(initial, [plans[0]['target'], plans[0]['companion_address']]) if fast else initial.read_memory(
        [plans[0]['target'], plans[0]['companion_address']])
    if len(data) != 2:
        raise ConsultError('short initial readback')
    report['initial_target'], report['initial_companion'] = data
    report['mode'] = 'fast' if fast else 'full_checks'
    report['sweep_kind'] = 'addresses' if address_mode else 'values'
    # With a unique value sweep, rotate rather than skip a value that already
    # matches: the original first value is still tested later in the sweep.
    plans = list(plans)
    values = [plan['value'] for plan in plans]
    if not address_mode and len(set(values)) == len(values) and len(values) > 1 and values[0] == data[0]:
        plans = plans[1:] + plans[:1]
    report['actual_order'] = [plan['value'] for plan in plans]
    report['actual_targets'] = [plan['target'] for plan in plans]
    report['status'] = 'running'
    report['trials'] = []
    for index, plan in enumerate(plans, 1):
        trial_started = time.monotonic()
        trial = {'index': index, 'value': plan['value'], 'target': plan['target'],
                 'command_hex': plan['command_hex'], 'mutation_attempted': False}
        report['trials'].append(trial)
        code = 0
        try:
            runner = run_fast_trial if fast else run_trial
            if not runner(client_factory(), plan, trial):
                code = 1
                report['status'] = 'stopped_on_mismatch'
        except AlreadyMatches as error:
            trial['status'] = 'already_matches' if address_mode else 'not_attempted'
            trial['skip_reason'] = str(error)
            if not address_mode:
                code = 2
                report['status'] = 'stopped_on_error'
        except (OSError, ValueError, ConsultError, KeyboardInterrupt) as error:
            trial['status'] = 'unverified' if trial['mutation_attempted'] else 'not_attempted'
            trial['error'] = f'{type(error).__name__}: {error}'
            code = 130 if isinstance(error, KeyboardInterrupt) else 2
            report['status'] = 'interrupted' if code == 130 else 'stopped_on_error'
        describe_checks(trial)
        trial['elapsed_seconds'] = round(time.monotonic() - trial_started, 4)
        report['elapsed_seconds'] = round(time.monotonic() - started, 4)
        report['matched_trials'] = sum(t.get('readback_matches', False) for t in report['trials'])
        report['verified_values'] = sorted({t['value'] for t in report['trials'] if t.get('readback_matches')})
        report['verified_addresses'] = sorted({t['target'] for t in report['trials'] if t.get('readback_matches')})
        report['already_matching_trials'] = sum(t['status'] == 'already_matches' for t in report['trials'])
        report['mismatched_trials'] = sum(t['status'] == 'readback_mismatch' for t in report['trials'])
        on_result(trial, report)
        if code and not (code == 1 and address_mode and continue_on_mismatch):
            return code
    report['status'] = 'completed_with_mismatches' if report['mismatched_trials'] else 'completed'
    report['all_256_values_verified'] = not address_mode and report['verified_values'] == list(range(256))
    if address_mode:
        report['all_planned_addresses_verified'] = report['verified_addresses'] == sorted(report['actual_targets'])
    return 1 if report['mismatched_trials'] else 0


CSV_FIELDS = ['trial', 'requested', 'before', 'after', 'verification',
              'companion_after', 'companion_verification', 'status', 'error', 'elapsed_seconds',
              'target_checks_match', 'companion_checks_match', 'target']


def csv_row(trial):
    target = f"{trial['target']:04X}"
    companion = f"{trial['target'] + 1:04X}"

    def value(phase, address):
        byte = trial.get(phase, {}).get(address)
        return '' if byte is None else f'{byte:02X}'

    return [trial['index'], f"{trial['value']:02X}", value('before', target),
            value('after', target), value('verification', target),
            value('after', companion), value('verification', companion),
            trial['status'], trial.get('error', trial.get('skip_reason', '')),
            trial.get('elapsed_seconds', ''), trial.get('target_readbacks_match', ''),
            trial.get('companion_readbacks_match', ''), target]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--target', type=lambda s: int(s, 16), default=0x0817)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--values', help='hex byte list/ranges; default 00-FF')
    selection.add_argument('--addresses', help='hex address list/ranges, e.g. 0740-083F or 0811,0813,0815')
    parser.add_argument('--value', type=lambda s: int(s, 16), help='fixed byte for --addresses; default 67')
    parser.add_argument('--continue-on-mismatch', action='store_true',
                        help='address mode: record completed readback mismatches and continue; errors still stop')
    parser.add_argument('--dev', default=DEFAULT_DEV)
    parser.add_argument('--full-checks', action='store_true',
                        help='slower: identity, reinitialization and full collateral snapshots per value')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true', help='execute live sweep; key on, engine off throughout')
    mode.add_argument('--dry-run', action='store_true', help='offline preview (default)')
    parser.add_argument('--output', type=Path, help='fresh JSON report path; CSV/log use same stem')
    args = parser.parse_args()
    address_mode = args.addresses is not None
    if not address_mode and (args.value is not None or args.continue_on_mismatch):
        parser.error('--value and --continue-on-mismatch require --addresses')
    try:
        if address_mode:
            requested_addresses = parse_ranges(args.addresses, 0xFFFF)
            fixed_value = 0x67 if args.value is None else args.value
            plans, unsupported = address_plans(requested_addresses, fixed_value)
            values = [plan['value'] for plan in plans]
        else:
            values = parse_values(args.values or '00-FF')
            plans = [plan_test(args.target, value) for value in values]
    except ValueError as error:
        parser.error(str(error))
    if address_mode:
        print(f'{len(plans)} modeled address trials with value ${fixed_value:02X}; each companion target+1 gets $0E.')
        print(f'{len(unsupported)} unsupported addresses:', ' '.join(f"{entry['target']:04X}" for entry in unsupported))
    else:
        print(f'{len(values)} trials at ${args.target:04X}; companion ${args.target+1:04X} = $0E.')
    print('Mode:', 'full checks' if args.full_checks else 'fast (one handshake; target-pair verification)')
    print('Keep the same key-on session, engine off. Each trial also changes forwarding state and other modeled RAM.')
    print('Order:', ' '.join(f"{plan['target']:04X}" for plan in plans) if address_mode else
          ' '.join(f'{value:02X}' for value in values))
    if not address_mode:
        print('A unique sweep rotates its first value to the end if it already matches the initial byte.')
    report = {'status': 'offline_preview', 'target': None if address_mode else args.target, 'requested_values': values,
              'mode': 'full_checks' if args.full_checks else 'fast',
              'model_validated': True, 'trials': [], 'all_256_values_verified': False,
              'key_session': 'operator keeps key on; script does not power-cycle or independently detect key cycles'}
    if address_mode:
        report.update(sweep_kind='addresses', requested_addresses=requested_addresses,
                      fixed_value=fixed_value, unsupported_addresses=unsupported,
                      planned_targets=[plan['target'] for plan in plans],
                      continue_on_mismatch=args.continue_on_mismatch)
    if not args.run:
        print('Offline models passed. Add --run to execute; no serial device was opened.')
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n')
        return 0
    suffix = '_address-sweep.json' if address_mode else '_direct-sweep.json'
    output = args.output or ROOT / 'logs' / (datetime.now().strftime('%Y-%m-%d_%H%M%S_%f') + suffix)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_log, table = output.with_suffix('.log'), output.with_suffix('.csv')
    if len({output, raw_log, table}) != 3 or any(path.exists() for path in (output, raw_log, table)):
        parser.error('choose a fresh .json output path; report/log/CSV paths must be distinct and unused')

    def save():
        temp = output.with_name(output.name + '.tmp')
        temp.write_text(json.dumps(report, indent=2) + '\n')
        temp.replace(output)

    transport = None
    code = 2
    report['status'] = 'starting'
    save()
    try:
        with table.open('x', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(CSV_FIELDS)
            stream.flush()

            def checkpoint(trial, current_report):
                writer.writerow(csv_row(trial))
                stream.flush()
                save()
                key = f"{trial['target']:04X}"
                print(f"[{trial['index']:3d}/{len(values)}] target={key} wanted={trial['value']:02X} "
                      f"{outcome_text(trial)} "
                      f"{trial['elapsed_seconds']:.2f}s", flush=True)
                if trial.get('error'):
                    print(trial['error'], file=sys.stderr, flush=True)

            transport = Transport(args.dev, str(raw_log))
            transport.note(f'direct sweep kind={report.get("sweep_kind", "values")}; '
                           f'addresses={args.addresses}; values={args.values}; same key-on requested')
            code = run_sweep(lambda: Consult(transport), plans, report, checkpoint, fast=not args.full_checks,
                             address_mode=address_mode, continue_on_mismatch=args.continue_on_mismatch)
    except (OSError, ValueError, ConsultError, KeyboardInterrupt) as error:
        report['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'stopped_on_error'
        report['error'] = f'{type(error).__name__}: {error}'
        code = 130 if isinstance(error, KeyboardInterrupt) else 2
        print(report['error'], file=sys.stderr)
    finally:
        try:
            if transport is not None:
                transport.close()
        finally:
            save()
    print(f"{report['status']}: {report.get('matched_trials', 0)}/{len(values)} matched; "
          f"{len(report.get('verified_values', []))} distinct values verified.")
    if address_mode:
        print(f"Addresses: {len(report.get('verified_addresses', []))} verified writes; "
              f"{report.get('already_matching_trials', 0)} already matched (not written); "
              f"{len(unsupported)} unsupported; {report.get('mismatched_trials', 0)} mismatches.")
    print(f'CSV: {table}\nReport: {output}\nRaw log: {raw_log}')
    return code


if __name__ == '__main__':
    sys.exit(main())
