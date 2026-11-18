#!/usr/bin/env python3
"""Probe the unknown $015AD1 helper with fixed X=$080E and varied [$080E].

The default is an offline instruction trace. --run performs one engine-off
trial on ECU 23710-2L904, with one mutation, an acknowledged stop, and
independent RAM readback. Repeat with a different --pointee in a fresh session.

The stream's address 19 samples $080F; it is not a synchronous read at the
helper call. Post-stop RAM can also change under normal ECU scheduling.
"""
import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from consult.experimental import mutation_stream, require_research_ecu
from consult.protocol import Consult, ConsultError
from consult.transport import DEFAULT_DEV, Transport
from trace_ram_write import HiddenRoutine

WATCH = [0x0717] + list(range(0x080A, 0x0811)) + [0x088B, 0x092A, 0x0CA5, 0x0C9D]
TAP = 0x080F


def plan_probe(pointee):
    if not 0 <= pointee <= 255:
        raise ValueError('pointee must be a byte')
    addresses = [0x5E00] * 15 + [0x5E22, 0x5E00, 0x5E08,
                                0x5E00 | pointee, TAP]
    model = HiddenRoutine(addresses).run()
    # Trace the shift, then the conditional call setup. This models the call
    # state if the ECU takes the gate at $8A65-$8A7E; it does not force that
    # gate to be taken on hardware.
    model.run(entry=0x8A50, stop_before=(0x8A65,),
              ranges=((0x8A50, 0x8A65),))
    model.run(entry=0x8A82, stop_before=(0x8A85,),
              ranges=((0x8A82, 0x8A86),))
    if (model.x, model.a & 0xFF, model.mem[0x080E]) != (0x080E, 0x0A, pointee):
        raise ValueError('instruction trace did not reach the expected call state')
    command = b''.join(bytes((0xC9, address >> 8, address & 255))
                       for address in addresses)
    return {
        'identity_required': '23710-2L904',
        'pointee': pointee,
        'addresses': addresses,
        'command_hex': command.hex(' '),
        'call_boundary': {'pc': 0x8A85, 'x': model.x, 'a_low': model.a & 0xFF,
                          'byte_at_x': model.mem[0x080E]},
        'model_scope': 'request builder, history shift, conditional call setup; gate, bank-1 helper, interrupts, and scheduler excluded',
        'request_builder_stores': [asdict(event) for event in model.stores
                                   if event.pc < 0x8A50 and event.iteration >= 15],
        'stream_tap': TAP,
        'readback_addresses': WATCH,
    }


def snapshot(client, addresses):
    result = {}
    for start in range(0, len(addresses), 8):
        chunk = addresses[start:start + 8]
        data = verified_read(client, chunk)
        if len(data) != len(chunk):
            raise ConsultError('short RAM readback')
        result.update({f'{address:04X}': byte
                       for address, byte in zip(chunk, data)})
    return result


def verified_read(client, addresses):
    if not 1 <= len(addresses) <= 8:
        raise ValueError('verified C9 read requires 1..8 addresses')
    payload = b''.join(bytes((0xC9, address >> 8, address & 255))
                       for address in addresses)
    data = None
    try:
        client.command(payload)
        data = client.read_frame(expected_len=len(addresses))
    finally:
        ack, _ = client.stop()
        if ack is None:
            raise ConsultError('C9 stop acknowledgment missing; session unverified')
    return data


def run_trial(client, plan, report):
    if client.init(ecu=0xED) is None:
        raise ConsultError('engine initialization failed')
    require_research_ecu(client)
    report['identity'] = '23710-2L904'
    report['before'] = snapshot(client, WATCH)
    # The call counter at $8A65 runs only while $088B.0 is set. Without it,
    # neither streaming frames nor a planted X would exercise $015AD1.
    if not (report['before']['088B'] & 0x01):
        raise ConsultError('$088B.0 is clear; helper gate inactive; no mutation sent')
    rpm_bytes = verified_read(client, [0x0995, 0x0994])
    if len(rpm_bytes) != 2:
        raise ConsultError('short RPM read; no mutation sent')
    report['rpm_before'] = int.from_bytes(rpm_bytes, 'big') * 12.5
    if report['rpm_before'] != 0:
        raise ConsultError('engine is running; no mutation sent')
    if report['before']['080E'] == plan['pointee']:
        raise ConsultError('baseline $080E already equals pointee; choose another byte')

    report['mutation_attempted'] = True
    frames = mutation_stream(client, bytes.fromhex(plan['command_hex']),
                             frames=2, expected_len=20)
    report['frames_hex'] = [frame.hex(' ') for frame in frames]
    report['stream_080f'] = [frame[19] for frame in frames]
    report['stop_acknowledged'] = True
    # No further mutation follows this readback, even when results are ambiguous.
    if client.init(ecu=0xED) is None:
        raise ConsultError('post-stop initialization failed; RAM unverified')
    report['after'] = snapshot(client, WATCH)
    report['changes'] = {key: {'before': report['before'][key], 'after': value}
                         for key, value in report['after'].items()
                         if value != report['before'][key]}
    report['status'] = 'observed'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pointee', type=lambda s: int(s, 16), default=0x31,
                        help='hex byte to place at $080E (default 31)')
    parser.add_argument('--dev', default=DEFAULT_DEV)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true', help='one live, engine-off trial')
    mode.add_argument('--dry-run', action='store_true', help='offline trace (default)')
    parser.add_argument('--output', type=Path, help='JSON report; live raw log uses the same stem')
    args = parser.parse_args(argv)
    try:
        plan = plan_probe(args.pointee)
    except ValueError as error:
        parser.error(str(error))
    print(f"Call boundary: X=${plan['call_boundary']['x']:04X}, "
          f"A(low)=${plan['call_boundary']['a_low']:02X}, "
          f"[$080E]=${plan['call_boundary']['byte_at_x']:02X}")
    print('C9 addresses:', ' '.join(f'${address:04X}' for address in plan['addresses']))
    report = {'plan': plan, 'mutation_attempted': False, 'status': 'offline_preview'}
    if not args.run:
        print('Offline trace only. Use --run for one key-on, engine-off trial.')
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n')
        return 0

    output = args.output or ROOT / 'logs' / (datetime.now().strftime('%Y-%m-%d_%H%M%S_%f') + '_bank1-x.json')
    raw_log = output.with_suffix('.log')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or raw_log.exists():
        parser.error('report or raw log already exists')
    transport = None
    code = 2
    try:
        transport = Transport(args.dev, str(raw_log))
        transport.note(f"bank1 fixed-X trial pointee=${args.pointee:02X}")
        run_trial(Consult(transport), plan, report)
        print('Stream $080F:', ' '.join(f'${value:02X}' for value in report['stream_080f']))
        print('Post-stop readback:', ' '.join(f'${key}=${value:02X}'
                                           for key, value in report['after'].items()))
        code = 0
    except (OSError, ValueError, ConsultError, KeyboardInterrupt) as error:
        report['status'] = 'unverified' if report['mutation_attempted'] else 'not_attempted'
        report['error'] = f'{type(error).__name__}: {error}'
        print(report['error'], file=sys.stderr)
        code = 130 if isinstance(error, KeyboardInterrupt) else 2
    finally:
        try:
            if transport is not None:
                transport.close()
        finally:
            output.write_text(json.dumps(report, indent=2) + '\n')
            print(f'Report: {output}; raw log: {raw_log}')
    return code


if __name__ == '__main__':
    sys.exit(main())
