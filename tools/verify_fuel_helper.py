#!/usr/bin/env python3
"""Execute actual 69F7..6A1F bytes with a small 7700 instruction subset.

Independent check of the closed-form helper, not a whole-ECU emulator or
hardware validation. Assumes 16-bit m/x, DT=0, Y=FFFF as in the normal caller.
"""
from pathlib import Path
import random
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from consult.fuel_math import bank_pulse_base


def execute(rom, incoming, correction, quantity, factor, additive, carry):
    memory = {0x0cd2: correction, 0x0906: quantity, 0x0a58: factor, 0x0a9c: additive}
    pc, a, b, y, c = 0x69f7, incoming, 0, 0xffff, carry
    def byte(address):
        return rom[address-0x1000]
    def operand(address):
        return byte(address) | byte(address+1)<<8
    for _ in range(100):
        op = byte(pc)
        if op in (0x6d, 0xe9):
            v = memory[operand(pc+1)] if op==0x6d else operand(pc+1)
            total = a+v+c if op==0x6d else a-v-(1-c)
            c = int(total>0xffff) if op==0x6d else int(total>=0)
            a = total & 0xffff; pc += 3
        elif op==0x38:
            c=1; pc+=1
        elif op==0x89 and byte(pc+1)==0x0d:
            product=a*memory[operand(pc+2)]
            a,b,c=product & 0xffff,product>>16,0; pc+=4
        elif op==0x89 and byte(pc+1)==0x28:
            a,b=b,a; pc+=2
        elif op==0x42 and byte(pc+1)==0x0a:
            c=int(bool(b&0x8000)); b=(b<<1)&0xffff; pc+=2
        elif op==0x2a:
            old=c; c=int(bool(a&0x8000)); a=((a<<1)|old)&0xffff; pc+=1
        elif op in (0xb0,0x90):
            delta=byte(pc+1); delta=delta-256 if delta>=128 else delta
            take=c if op==0xb0 else not c
            pc+=2+(delta if take else 0)
        elif op==0x98:
            a=y; pc+=1
        elif op==0x6b:
            return a
        else:
            raise ValueError(f'unsupported opcode {op:02X} at {pc:04X}')
    raise ValueError('helper did not return')


def main():
    rom=Path('rom/23710-2L904_1000-FFFF.bin').read_bytes()
    rng=random.Random(904)
    cases=[(0xa000,0xa800,1234,0x4000,77,0),
           (0xc7ff,0,0xffff,0,0,0)]
    cases += [tuple(rng.randrange(65536) for _ in range(5))+(rng.randrange(2),) for _ in range(10000)]
    for values in cases:
        actual=execute(rom,*values)
        expected=bank_pulse_base(*values[:5],incoming_carry=values[5])
        if actual!=expected:
            raise AssertionError((values, actual, expected))
    print(f'{len(cases)} actual-ROM helper executions match the reconstructed formula.')


if __name__=='__main__':
    main()
