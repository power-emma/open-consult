#!/usr/bin/env python3
"""Offline instruction trace of Consult RX parsing and native fuel overrides.

Runs selected actual ROM paths. UART ready/data status and scheduler entry are
supplied explicitly. Interrupt timing, physical engine behavior and bank 1 are
not emulated. No serial device is opened.
"""
import argparse
import json
from pathlib import Path

from trace_ram_write import HiddenRoutine
from fuel_control_test import ADDRESSES, build_command


class ConsultTrace:
    def __init__(self, initial=None):
        self.cpu = HiddenRoutine([0], initial)
        self.cpu.mem[0x071B] = 4  # already initialized, waiting for a command
        self.cpu.mem[0x073B] = self.cpu.mem[0x073C] = 0
        self.echoes = []

    def feed(self, byte):
        cpu = self.cpu
        if cpu.calls or cpu.stack:
            raise RuntimeError('unbalanced logical stack before next UART byte')
        cpu.mem[0x0737] = byte
        cpu.mem[0x07C2] = 0x0A  # receive data + transmit ready, no UART error
        cpu.mem[0x0035] = 0x02  # immediate transmit-ready echo path
        cpu.m = 1             # ISR's SEM before parser entry
        first = len(cpu.stores)
        cpu.run(entry=0x4F6E, stop_before=(0x5437,), ranges=((0x4F6E, 0x551F),))
        echo = [store.value for store in cpu.stores[first:] if store.address == 0x0032]
        self.echoes.extend(echo)
        return bytes(echo)

    def send(self, command):
        return b''.join(self.feed(byte) for byte in command)

    def build_frame_payload(self):
        cpu = self.cpu
        if not cpu.mem[0x071B] & 0x20:
            raise ValueError('parser did not enter streaming state')
        cpu.m = 1
        cpu.run(entry=0x9AD6, stop_before=(0x9C00, 0x9CDC), ranges=((0x9AD6, 0x9D3F),))
        count = cpu.b & 255
        return bytes(cpu.mem[0x0740:0x0740 + count])

    def apply_native_fuel(self):
        """Run each bank's override/clamp/report tail; no ADC/engine emulation."""
        cpu = self.cpu
        if not cpu.mem[0x07B7] & 2:
            raise ValueError('native fuel active flag is not set')
        for x, y, bank_flag in ((0x0B08, 0x0B44, 0x20), (0x0B26, 0x0B5A, 0)):
            cpu.x, cpu.y, cpu.m = x, y, 1
            cpu.mem[0x093C] = (cpu.mem[0x093C] & ~0x20) | bank_flag
            cpu.mem[0x0AF8:0x0AFA] = y.to_bytes(2, 'little')
            cpu.run(entry=0x6E15, stop_before=(0x745B,),
                    ranges=((0x6E15, 0x6E35), (0x7415, 0x745B)))


def trace_fuel_request(percent):
    trace = ConsultTrace({0x0994: 80})  # synthetic RPM sample, not a running engine
    command = build_command(percent)
    echoes = trace.send(command)
    trace.send(b'\xF0')
    parsed = {
        'cs_state': trace.cpu.mem[0x071B], 'cs_flags': trace.cpu.mem[0x071C],
        'argc': trace.cpu.mem[0x073B], 'active_count': trace.cpu.mem[0x073C],
        'requested_flags': trace.cpu.mem[0x07AC], 'active_flags': trace.cpu.mem[0x07B7],
        'test_value': trace.cpu.mem[0x0770], 'forwarded_count': trace.cpu.mem[0x07E1],
    }
    trace.apply_native_fuel()
    payload = trace.build_frame_payload()
    applied = {'alpha_a': trace.cpu.mem[0x0730], 'alpha_b': trace.cpu.mem[0x0731]}
    stop_echo = trace.send(b'\x30')
    return {
        'evidence': 'selected ROM paths with synthetic UART status and RAM; not hardware validation',
        'command_hex': command.hex(' '), 'echo_hex': echoes.hex(' '), 'parsed': parsed,
        'applied': applied, 'telemetry_payload_hex': payload.hex(' '),
        'telemetry_addresses': list(ADDRESSES), 'stop_echo_hex': stop_echo.hex(' '),
        'active_flags_after_stop': trace.cpu.mem[0x07B7],
        'instruction_count': trace.cpu.steps,
        'executed_pcs': sorted(set(trace.cpu.executed)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--percent', type=int, default=103)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = trace_fuel_request(args.percent)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    for key in ('evidence', 'parsed', 'applied', 'telemetry_payload_hex',
                'stop_echo_hex', 'active_flags_after_stop', 'instruction_count'):
        print(f'{key}: {result[key]}')


if __name__ == '__main__':
    main()
