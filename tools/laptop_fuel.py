#!/usr/bin/env python3
"""Bounded laptop RPM/load fuel-feedback controller, native Consult test 81.

Preview: python3 tools/laptop_fuel.py --map maps/native-fuel-stock.json
Live:    python3 tools/laptop_fuel.py --fixed-percent 103 --seconds 10 --run

ROM-derived control and mixed telemetry are not hardware-validated yet. null
map cells mean normal ECU feedback; numeric 100 is a fixed override. Commands
are changed only after acknowledged STOP. No mutation retries or ROM writes.
"""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from consult.experimental import require_research_ecu
from consult.fuel_map import FuelMap
from consult.protocol import Consult, ConsultError
from consult.transport import DEFAULT_DEV, Transport
from c9_direct_sweep import read_checked
from fuel_control_test import ADDRESSES, build_command, decode_sample


def telemetry_command():
    return b''.join(bytes((0xC9, address >> 8, address & 255)) for address in ADDRESSES)


class MapSource:
    def __init__(self, path=None, percent=None, reload=False):
        self.path, self.reload = path, reload
        self.signature = None
        self.digest = None
        self.grid = FuelMap.constant(percent) if path is None else self._read()

    def _read(self):
        raw = self.path.read_bytes()
        grid = FuelMap(json.loads(raw))
        stat = self.path.stat()
        self.signature = (stat.st_mtime_ns, stat.st_size)
        self.digest = hashlib.sha256(raw).hexdigest()
        return grid

    def lookup(self, rpm, load_code):
        if self.path is not None and self.reload:
            stat = self.path.stat()
            if self.signature != (stat.st_mtime_ns, stat.st_size):
                self.grid = self._read()
        return self.grid.lookup(rpm, load_code)


def stop_checked(client):
    ack, _ = client.stop(timeout=0.5)
    if ack is None:
        raise ConsultError('stop acknowledgment missing; no further control request sent')


def run_controller(client, lookup, seconds, report, on_sample, on_event,
                   *, clock=time.monotonic, settle_timeout=1.0):
    """Keep unchanged requests streaming; STOP/read/reselect on a map change."""
    started = clock()
    report.update(status='running', requests=[], sample_count=0)
    primary = cleanup = None
    current = None
    consecutive = 0
    requested_at = None
    event = None

    def choose_from_baseline():
        data = read_checked(client, [0x0995, 0x0994, 0x0ABE, 0x0ABD])
        rpm = int.from_bytes(data[:2], 'big') * 12.5
        if rpm == 0:
            raise ConsultError('engine is not running; no new control request sent')
        return lookup(rpm, int.from_bytes(data[2:], 'big'))

    def request(percent, stop_started=None):
        nonlocal current, consecutive, requested_at, event
        command = telemetry_command() if percent is None else build_command(percent)
        event = {'percent': percent, 'attempted_at_seconds': round(clock() - started, 4),
                 'verified': False, 'command_hex': command.hex(' ')}
        report['requests'].append(event)
        on_event(event, report)
        # Even the stock stream has no retry: state/echo failures end this run.
        client.command(command, retries=0, mutation=percent is not None)
        current, consecutive, requested_at = percent, 0, clock()
        event['request_ack_at_seconds'] = round(requested_at - started, 4)
        if stop_started is not None:
            event['stop_to_request_ack_seconds'] = round(requested_at - stop_started, 4)

    try:
        request(choose_from_baseline())
        while clock() - started < seconds:
            data = client.read_frame(expected_len=len(ADDRESSES), timeout=1.0)
            sample = decode_sample(data, 100 if current is None else current)
            sample.update(elapsed_seconds=round(clock() - started, 4), requested_percent=current)
            if sample['rpm'] == 0:
                raise ConsultError('engine stopped; ending laptop fuel control')
            applied = (not bool(sample['active_flags'] & 2)) if current is None else sample['both_banks_match']
            sample['control_matches'] = applied
            consecutive = consecutive + 1 if applied else 0
            report['sample_count'] += 1
            report['last_sample'] = sample
            on_sample(sample, report)
            if consecutive >= 3 and not event['verified']:
                event['verified'] = True
                event['verified_at_seconds'] = round(clock() - started, 4)
                on_event(event, report)
            if not applied and clock() - requested_at > settle_timeout:
                raise ConsultError('requested fuel-control state did not settle within the verification timeout')
            if consecutive >= 3 and clock() - started < seconds:
                desired = lookup(sample['rpm'], sample['load_code'])
                if desired != current:
                    stop_started = clock()
                    stop_checked(client)
                    # Acknowledged release, fresh RPM/load and read stop are
                    # required before issuing the next native parameter.
                    request(choose_from_baseline(), stop_started)
        report['status'] = 'completed' if all(item['verified'] for item in report['requests']) else 'not_verified'
    except BaseException as error:
        primary = error
        report['status'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'unverified'
    finally:
        try:
            stop_checked(client)
            report['final_stop_acknowledged'] = True
        except BaseException as error:
            cleanup = error
    if primary is not None or cleanup is not None:
        report['error'] = f'primary={primary!r}; cleanup={cleanup!r}'
        if isinstance(primary, (KeyboardInterrupt, SystemExit)):
            raise primary
        raise ConsultError(report['error']) from primary
    # Verify software override release, not an assumed restoration to alpha=100.
    flags = read_checked(client, [0x07B7])[0]
    report['active_flags_after_stop'] = flags
    report['override_released'] = not bool(flags & 2)
    if not report['override_released']:
        report['status'] = 'not_verified'
    report['elapsed_seconds'] = round(clock() - started, 4)
    return report['status'] == 'completed'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--map', type=Path, help='JSON RPM/load-code map')
    source.add_argument('--fixed-percent', type=int, help='fixed decimal native percentage 75..125')
    parser.add_argument('--reload-map', action='store_true', help='reload a changed map file during the run')
    parser.add_argument('--seconds', type=float, default=10.0, help='bounded run duration, default 10 seconds')
    parser.add_argument('--dev', default=DEFAULT_DEV)
    parser.add_argument('--run', action='store_true', help='open cable and control fuel feedback; engine running')
    parser.add_argument('--output', type=Path, help='fresh JSON report path; .log and .samples.jsonl share stem')
    args = parser.parse_args()
    try:
        if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 600:
            raise ValueError('duration must be finite and in 1..600 seconds')
        if args.reload_map and args.map is None:
            raise ValueError('--reload-map requires --map')
        map_source = MapSource(args.map, args.fixed_percent, args.reload_map)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    print(f'Laptop fuel feedback: {args.seconds:g}s, native range 75..125%; null = normal ECU control.')
    for rpm, load in ((750, 0), (2000, 8192), (4000, 32768)):
        print(f'  RPM={rpm}, raw load={load}: {map_source.lookup(rpm, load)}')
    if not args.run:
        print('Offline preview; no serial device opened. Add --run for a bounded live test.')
        return 0
    output = args.output or ROOT / 'logs' / (datetime.now().strftime('%Y-%m-%d_%H%M%S_%f') + '_laptop-fuel.json')
    raw_log, sample_log = output.with_suffix('.log'), output.with_suffix('.samples.jsonl')
    if len({output, raw_log, sample_log}) != 3 or any(path.exists() for path in (output, raw_log, sample_log)):
        parser.error('report/log/sample paths must be distinct and unused')
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'status': 'starting', 'map_path': str(args.map) if args.map else None,
              'initial_map_sha256': map_source.digest, 'fixed_percent': args.fixed_percent,
              'duration_requested_seconds': args.seconds, 'requests': []}
    transport = None
    code = 2

    def save():
        temporary = output.with_name(output.name + '.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(output)

    save()
    try:
        with sample_log.open('x') as samples:
            def on_sample(sample, state):
                sample['map_sha256'] = map_source.digest
                samples.write(json.dumps(sample) + '\n')
                samples.flush()

            def on_event(event, state):
                save()
                print(f"{event['attempted_at_seconds']:.2f}s percent={event['percent']} verified={event['verified']}", flush=True)

            transport = Transport(args.dev, str(raw_log))
            client = Consult(transport)
            if client.init(ecu=0xED) is None:
                raise ConsultError('engine initialization failed')
            require_research_ecu(client)
            verified = run_controller(client, map_source.lookup, args.seconds, report, on_sample, on_event)
            code = 0 if verified else 1
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
            report['final_map_sha256'] = map_source.digest
            save()
            print(f"{report['status']}: {report.get('sample_count', 0)} samples, "
                  f"{len(report['requests'])} requests; released={report.get('override_released')}")
            print(f'Report: {output}\nSamples: {sample_log}\nRaw log: {raw_log}')
    return code


if __name__ == '__main__':
    sys.exit(main())
