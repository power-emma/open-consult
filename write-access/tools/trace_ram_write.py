#!/usr/bin/env python3
"""Offline execution trace of the ROM's $543F request-building routine.

This is a deliberately limited M7700 instruction interpreter, not a vehicle
emulator. It executes actual ROM bytes with m tracked at every instruction,
bank/direct page 0 and 16-bit X/Y. No serial device is opened. Interrupts,
scheduler tasks, mailbox arrivals and actuator behavior are not simulated.
"""
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from m7700dis import Rom, decode

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Store:
    pc: int
    iteration: int
    address: int
    width: int
    before: int
    value: int


class HiddenRoutine:
    """Execute only $543F-$54C6; unsupported instructions fail explicitly."""
    def __init__(self, addresses, initial=None):
        if not 1 <= len(addresses) <= 20 or any(not 0 <= a <= 0xFFFF for a in addresses):
            raise ValueError('requires 1..20 16-bit request addresses')
        self.rom = Rom((ROOT / 'rom/23710-2L904_1000-FFFF.bin').read_bytes(), 0x1000)
        self.mem = bytearray(65536)
        self.mem[0x1000:] = self.rom.data
        for addr, value in (initial or {}).items():
            if not 0 <= addr < 0x1000 or not 0 <= value <= 255:
                raise ValueError('initial state must contain low-RAM byte values')
            self.mem[addr] = value
        # cs_argbuf holds the received address HIGH byte first. $5464 rotates
        # the little-endian word read back into the requested 16-bit address.
        for index, address in enumerate(addresses):
            self.mem[0x08D2 + 2 * index:0x08D4 + 2 * index] = address.to_bytes(2, 'big')
        self.mem[0x073B] = len(addresses) * 2
        self.a = self.b = self.x = self.y = 0
        self.m = 1
        self.c = self.z = self.n = False
        self.pc = 0x543F
        self.stores = []
        self.steps = 0
        self.calls = []
        self.stack = []
        self.executed = []

    @property
    def width(self):
        return 1 if self.m else 2

    def read(self, addr, width):
        return int.from_bytes(self.mem[addr:addr + width], 'little')

    def write(self, addr, value, width):
        value &= (1 << (8 * width)) - 1
        before = self.read(addr, width)
        self.stores.append(Store(self.pc, self.mem[0x0C48], addr, width, before, value))
        self.mem[addr:addr + width] = value.to_bytes(width, 'little')

    def flags(self, value, width):
        mask = (1 << (width * 8)) - 1
        self.z = (value & mask) == 0
        self.n = bool(value & (1 << (width * 8 - 1)))

    def put(self, register, value):
        width = 2 if register in ('x', 'y') else self.width
        mask = (1 << (width * 8)) - 1
        old = getattr(self, register)
        setattr(self, register, (old & ~mask) | (value & mask))
        self.flags(value, width)

    def address(self, operand):
        match = re.fullmatch(r'\$([0-9A-F]+)(,[XY])?', operand)
        if not match:
            raise ValueError(f'unsupported address {operand}')
        index = getattr(self, match[2][1].lower()) if match[2] else 0
        return (int(match[1], 16) + index) & 0xFFFF

    def operand(self, text, width=None):
        return int(text[2:], 16) if text.startswith('#$') else self.read(
            self.address(text), width or self.width)

    def run(self, max_steps=3000, *, entry=None, stop_before=(),
            ranges=((0x543F, 0x54C7),)):
        """Execute within explicit ranges; the original hidden routine is default.

        Extended traces use logical call/data stacks, not interrupt timing or
        a mapped CPU hardware stack. Unsupported instructions still fail.
        """
        if entry is not None:
            self.pc = entry
        start_steps = self.steps
        while self.steps - start_steps < max_steps:
            if self.pc in stop_before:
                return self
            if not any(start <= self.pc < end for start, end in ranges):
                raise RuntimeError(f'execution left modeled ranges at ${self.pc:04X}')
            inst = decode(self.rom, self.pc, self.m, 0)
            name, arg = inst.name, inst.text
            next_pc = self.pc + inst.size
            width, mask = self.width, (1 << (8 * self.width)) - 1
            self.steps += 1
            self.executed.append(self.pc)
            if name in ('RTL', 'RTS'):
                if not self.calls:
                    return self
                self.pc = self.calls.pop()
                continue
            if name in ('SEM', 'CLM'):
                self.m = int(name == 'SEM')
            elif name in ('CLC', 'SEC'):
                self.c = name == 'SEC'
            elif name in ('LDA', 'LDB', 'LDX', 'LDY'):
                register = name[-1].lower()
                self.put(register, self.operand(arg, 2 if register in ('x', 'y') else width))
            elif name in ('STA', 'STB', 'STX', 'STY'):
                register = name[-1].lower()
                self.write(self.address(arg), getattr(self, register), 2 if register in ('x', 'y') else width)
            elif name == 'LDM':
                address, literal = arg.rsplit(',', 1)
                self.write(self.address(address), self.operand(literal), width)
            elif name in ('CLB', 'SEB'):
                address, literal = arg.split(',')
                address = self.address(address)
                bits = self.operand(literal)
                value = self.read(address, width)
                self.write(address, value & ~bits if name == 'CLB' else value | bits, width)
            elif name in ('BBC', 'BBS'):
                address, literal, _ = arg.split(',')
                present = bool(self.read(self.address(address), width) & self.operand(literal))
                if present == (name == 'BBS'):
                    next_pc = inst.targets[0]
            elif name in ('BCC', 'BCS', 'BEQ', 'BNE', 'BRA', 'BMI', 'BPL'):
                take = {'BCC': not self.c, 'BCS': self.c, 'BEQ': self.z,
                        'BNE': not self.z, 'BRA': True, 'BMI': self.n, 'BPL': not self.n}[name]
                if take:
                    next_pc = inst.targets[0]
            elif name in ('CPX', 'CPY', 'CMP', 'CMPB'):
                register = {'CPX': 'x', 'CPY': 'y', 'CMP': 'a', 'CMPB': 'b'}[name]
                cmp_width = 2 if register in ('x', 'y') else width
                lhs = getattr(self, register) & ((1 << (8 * cmp_width)) - 1)
                rhs = self.operand(arg, cmp_width)
                self.c = lhs >= rhs
                self.flags(lhs - rhs, cmp_width)
            elif name in ('AND', 'ANDB', 'ORA', 'ORB', 'EOR', 'EORB'):
                register = 'b' if name.endswith('B') else 'a'
                lhs, rhs = getattr(self, register), self.operand(arg)
                value = lhs & rhs if name.startswith('AND') else lhs ^ rhs if name.startswith('EOR') else lhs | rhs
                self.put(register, value)
            elif name in ('ADC', 'ADCB', 'SBC', 'SBCB'):
                register = 'b' if name.endswith('B') else 'a'
                lhs, rhs = getattr(self, register) & mask, self.operand(arg)
                add = name.startswith('ADC')
                value = lhs + rhs + int(self.c) if add else lhs - rhs - int(not self.c)
                self.c = value > mask if add else value >= 0
                self.put(register, value)
            elif name in ('ASL', 'LSR', 'LSRB') and arg in ('A', 'B'):
                register = 'b' if arg == 'B' or name == 'LSRB' else 'a'
                value = getattr(self, register) & mask
                self.c = bool(value & (1 << (width * 8 - 1))) if name == 'ASL' else bool(value & 1)
                self.put(register, value << 1 if name == 'ASL' else value >> 1)
            elif name == 'RLA':
                shift = self.operand(arg) % (width * 8)
                value = self.a & mask
                self.put('a', (value << shift) | (value >> (width * 8 - shift)))
            elif name == 'MPY':
                product = (self.a & mask) * self.operand(arg)
                self.put('a', product & mask)
                self.put('b', product >> (width * 8))
            elif name in ('TAX', 'TXA', 'TXB', 'TBY', 'TYA', 'TAY', 'TBX', 'TYB'):
                dst, src = {'TAX': ('x', 'a'), 'TXA': ('a', 'x'),
                            'TXB': ('b', 'x'), 'TBY': ('y', 'b'), 'TYA': ('a', 'y'),
                            'TAY': ('y', 'a'), 'TBX': ('x', 'b'), 'TYB': ('b', 'y')}[name]
                self.put(dst, getattr(self, src))
            elif name == 'XAB':
                a, b = self.a, self.b
                self.put('a', b)
                self.put('b', a)
            elif name in ('INC', 'DEC'):
                address = self.address(arg)
                value = self.read(address, width) + (1 if name == 'INC' else -1)
                self.write(address, value, width)
                self.flags(value, width)
            elif name in ('INA', 'DEA', 'INB', 'DEB', 'INX', 'DEX', 'INY', 'DEY'):
                register = name[-1].lower()
                self.put(register, getattr(self, register) + (1 if name.startswith('IN') else -1))
            elif name in ('JMP', 'JML', 'JSL', 'JSR') and arg.startswith('$'):
                if name in ('JSL', 'JSR'):
                    self.calls.append(next_pc)
                next_pc = int(arg[1:], 16)
            elif name in ('PHA', 'PHB', 'PHX', 'PHY'):
                register = name[-1].lower()
                self.stack.append(getattr(self, register) & (0xFFFF if register in ('x', 'y') else mask))
            elif name in ('PLA', 'PLB', 'PLX', 'PLY'):
                self.put(name[-1].lower(), self.stack.pop())
            elif name in ('PSH', 'PUL') and arg == '#$02':
                if name == 'PSH':
                    self.stack.append(self.b & mask)
                else:
                    self.put('b', self.stack.pop())
            elif name in ('SEI', 'CLI', 'NOP'):
                pass  # no concurrent interrupts are modeled
            else:
                raise NotImplementedError(f'${self.pc:04X}: {name} {arg}')
            self.pc = next_pc
        raise RuntimeError('routine exceeded instruction limit')


def direct_payload(target, value, companion=0x0E):
    """Candidate last-word store: chosen low byte at an odd RAM address.

    The caller must execute/check it: control-field aliases can change results.
    High companion byte must keep the request inside the forwarding window.
    """
    if not 0x07C3 <= target <= 0x083F or target % 2 != 1:
        raise ValueError('direct word-store low byte requires an odd address in $07C3-$083F')
    if not 0 <= value <= 255 or not 0 <= companion <= 255:
        raise ValueError('byte values must be in 0..255')
    n = (target - 0x07C3) // 2
    steer = 0x5E00 + ((n - 1) & 0xFF)
    word = 0x5000 + (companion << 8) + value
    if not 0x5D40 <= word <= 0x623F:
        raise ValueError('requested word would be outside the forwarded address range')
    return [0x5E00] * 15 + [steer, word]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=lambda x: int(x, 16), default=0x0817)
    parser.add_argument('--value', type=lambda x: int(x, 16), default=0x42)
    parser.add_argument('--json', type=Path, help='save full modeled store trace')
    args = parser.parse_args()
    payload = direct_payload(args.target, args.value)
    routine = HiddenRoutine(payload).run()
    # Last request can also be followed by a local readback address without
    # adding another forwarded entry. It is deliberately omitted here.
    print('OFFLINE ONLY: no serial connection; result is at return from $543F, before background tasks.')
    print('Request addresses:', ' '.join(f'{addr:04X}' for addr in payload))
    for event in routine.stores:
        if event.iteration >= 15:
            print(f'PC={event.pc:04X} i={event.iteration:02d} [{event.address:04X}] '
                  f'width={event.width} {event.before:0{event.width*2}X}->{event.value:0{event.width*2}X}')
    actual = routine.mem[args.target]
    print(f'At routine return: [{args.target:04X}]={actual:02X}; requested={args.value:02X}')
    if args.json:
        result = {'evidence': 'ROM-instruction model, not hardware validation',
                  'target': args.target, 'requested': args.value, 'actual': actual,
                  'addresses': payload, 'steps': routine.steps,
                  'stores': [asdict(event) for event in routine.stores]}
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
