#!/usr/bin/env python3
"""Reproduce table identity checks without assigning unverified physical units."""
import argparse
import hashlib
import json
from pathlib import Path

REGIONS = {
    'maf_curve': (0x1220, 128), 've': (0x1400, 256),
    've_axes': (0x1500, 32), 'fuel': (0x1700, 256),
    'knock_fuel': (0x1800, 256), 'fuel_axes': (0x1900, 32),
    'timing': (0x1d00, 256), 'knock_timing': (0x1e00, 256),
    'timing_axes': (0x1f00, 32),
}


def region(data, base, address, size):
    offset = address - base
    if offset < 0 or offset + size > len(data):
        raise ValueError(f'region {address:04X}+{size:X} outside supplied dump')
    return data[offset:offset + size]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump', type=Path)
    p.add_argument('--base', type=lambda x: int(x, 0), required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--reference-base', type=lambda x: int(x, 0), default=0)
    args = p.parse_args()
    data, reference = args.dump.read_bytes(), args.reference.read_bytes()
    result = {'dump_sha256': hashlib.sha256(data).hexdigest(),
              'reference_sha256': hashlib.sha256(reference).hexdigest(),
              'interpretation': 'Candidate layout; equality does not establish scaling or consumers.',
              'regions': {}}
    for name, (address, size) in REGIONS.items():
        x = region(data, args.base, address, size)
        y = region(reference, args.reference_base, address, size)
        result['regions'][name] = {'address': hex(address), 'size': size,
            'identical': x == y, 'different_offsets': [hex(address+i) for i, (a,b) in enumerate(zip(x,y)) if a != b],
            'raw_min': min(x), 'raw_max': max(x),
            'sha256': hashlib.sha256(x).hexdigest()}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
