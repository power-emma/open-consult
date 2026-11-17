#!/usr/bin/env python3
"""Read-only intermediate table research capture for ECU 23710-2L904.

Default prints the request without opening a cable. Add --run to capture.
Raw coefficients are deliberately not labeled AFR, percent, or table outputs.
"""
import argparse
import csv
import math
from datetime import datetime
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from consult.experimental import require_research_ecu
from consult.protocol import Consult, ConsultError
from consult.transport import DEFAULT_DEV, Transport

ADDRESSES = (0x0995, 0x0994, 0x0ABE, 0x0ABD, 0x09F0, 0x09B1,
             0x0BA6, 0x0DB8, 0x0DCF, 0x0A74, 0x0A75, 0x0A70,
             0x0DAA, 0x0DA9, 0x0DAC, 0x0DAB, 0x0730, 0x0731,
             0x0732, 0x07B7)
PAYLOAD = b''.join(bytes((0xC9, a >> 8, a & 255)) for a in ADDRESSES)


def decode(data):
    if len(data) != len(ADDRESSES):
        raise ValueError('incorrect trace frame length')
    signed = lambda x: x if x < 128 else x - 256
    return dict(rpm=((data[0] << 8) | data[1]) * 12.5,
                load_code=(data[2] << 8) | data[3], tps_mv=data[4] * 20,
                rpm_index_raw=data[5], timing_base_raw=data[6],
                timing_base_signed_candidate=signed(data[6]),
                knock_term_raw=data[7], mode_0dcf_raw=data[8],
                fuel_0a74_word_raw=data[9] | (data[10] << 8),
                fuel_0a70_raw=data[11],
                injector_a_ms=((data[12] << 8) | data[13]) / 100,
                injector_b_ms=((data[14] << 8) | data[15]) / 100,
                alpha_a=data[16], alpha_b=data[17], timing_btdc=110-data[18],
                active_flags_raw=data[19], raw_hex=data.hex(' '))


FUEL_ADDRESSES = (0x09B1, 0x0ABE, 0x0ABD, 0x09F0,
                  0x0A56, 0x0A57, 0x0A58, 0x0A59,
                  0x0A9C, 0x0A9D, 0x0A74, 0x0A70,
                  0x0AC7, 0x0AC8, 0x0ADB, 0x0ADC,
                  0x0CD2, 0x0CD3, 0x09B4, 0x0DCF)


def decode_fuel(data):
    if len(data) != 20:
        raise ValueError('incorrect fuel trace frame length')
    word_at = lambda i: data[i] | data[i+1] << 8
    return dict(rpm_index_raw=data[0], rpm_index_rpm=data[0]*50,
                load_code=(data[1]<<8)|data[2],
                calculated_load=((data[1]<<8)|data[2])/256,
                tps_mv=data[3]*20, composite_0a56_raw=word_at(4),
                factor_0a58_raw=word_at(6), additive_0a9c_raw=word_at(8),
                fuel_0a74_byte_raw=data[10], fuel_0a70_raw=data[11],
                base_0ac7_raw=word_at(12), term_0adb_raw=word_at(14),
                correction_0cd2_raw=word_at(16), adjusted_tps_raw=data[18],
                mode_0dcf_raw=data[19], raw_hex=data.hex(' '))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dev', default=DEFAULT_DEV)
    p.add_argument('--run', action='store_true')
    p.add_argument('--profile', choices=['timing', 'fuel'], default='timing')
    p.add_argument('--seconds', type=float, default=0, help='duration in seconds; 0 records until Ctrl+C (default)')
    args = p.parse_args()
    if not math.isfinite(args.seconds) or args.seconds < 0:
        p.error('--seconds must be finite and nonnegative; 0 records until Ctrl+C')
    addresses = FUEL_ADDRESSES if args.profile == 'fuel' else ADDRESSES
    decoder = decode_fuel if args.profile == 'fuel' else decode
    payload = b''.join(bytes((0xC9, a >> 8, a & 255)) for a in addresses)
    print('Read-only C9 addresses:', ' '.join(f'{a:04X}' for a in addresses))
    if not args.run:
        print('Preview only. Add --run to open the cable.'); return 0
    stem = ROOT / 'logs' / (datetime.now().strftime('%Y-%m-%d_%H%M%S_%f') + ('_fuel-trace' if args.profile == 'fuel' else '_table-trace'))
    stem.parent.mkdir(parents=True, exist_ok=True)
    transport = None
    client = None
    started_stream = False
    code = 0
    print(f'CSV: {stem.with_suffix(".csv")}\nRaw log: {stem.with_suffix(".log")}', flush=True)
    try:
        with stem.with_suffix('.csv').open('x', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=['seconds'] + list(decoder(bytes(20))))
            writer.writeheader(); output.flush()
            transport = Transport(args.dev, str(stem.with_suffix('.log')))
            client = Consult(transport)
            if client.init(ecu=0xED) is None:
                raise ConsultError('ECU initialization failed')
            require_research_ecu(client)
            transport.note('table-trace addresses: ' + ' '.join(f'{a:04X}' for a in addresses))
            started_stream = True
            client.command(payload, retries=0)
            start = time.monotonic()
            last_print = -1.0
            while args.seconds == 0 or time.monotonic() - start < args.seconds:
                sample = decoder(client.read_frame(expected_len=20, timeout=1.0))
                elapsed = time.monotonic() - start
                writer.writerow(dict(seconds=round(elapsed, 6), **sample)); output.flush()
                if elapsed-last_print >= 0.2:
                    print(f'{elapsed:7.2f}s ' + ' '.join(f'{k}={v}' for k,v in sample.items() if k != 'raw_hex'), flush=True)
                    last_print = elapsed
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, ConsultError, TimeoutError) as error:
        print(str(error), file=sys.stderr); code = 2
    finally:
        try:
            if client is not None and started_stream:
                ack, _ = client.stop(timeout=0.5)
                if ack is None:
                    print('STOP acknowledgment missing.', file=sys.stderr); code = 2
        finally:
            if transport is not None:
                transport.close()
    return code


if __name__ == '__main__':
    sys.exit(main())
