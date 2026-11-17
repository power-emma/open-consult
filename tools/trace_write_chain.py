#!/usr/bin/env python3
"""Compare ROM-instruction schedules for a lower-RAM write chain, offline only.

UART/receive and scheduler ordering are selected test conditions, not measured
hardware timing. This script has no serial I/O. It does not establish a reliable
chosen-value write through the mailbox-dependent reply builder.
"""
import argparse
import json
from pathlib import Path

from trace_consult_parser import ConsultTrace


def c9_command(addresses):
    return b''.join(bytes((0xC9, address >> 8, address & 255)) for address in addresses)


def receive_pending(trace, value):
    cpu = trace.cpu
    cpu.mem[0x021F] = 1
    cpu.mem[0x029E] = 0x20  # synthetic type-0 message ready, no upper busy bit
    cpu.mem[0x02B6] = value
    cpu.m = 1
    cpu.run(entry=0xC7F5, ranges=((0xC7F5, 0xCBA2),))


def conditional_payload(target, value):
    if not 0x0740 <= target <= 0x083F or not 0 <= value <= 255:
        raise ValueError('target/value outside downstream byte-write range')
    return [0x5E00] * 15 + [0x5E0A, 0x5E0B, 0x5E00 + target - 0x0740,
                            0x5E00 + value, 0x0817]


def schedule_case(schedule, target=0x0770, value=103, mailbox_value=0x93):
    trace = ConsultTrace()
    # A native 100% fuel request is committed on the same F0. Its two value
    # bytes are separate from cs_argbuf; the ROM still accepts 20 C9 addresses.
    prefix = bytes([0x0A, 0x81, 100]) if target == 0x0770 else b''
    command = prefix + c9_command(conditional_payload(target, value))
    echoes = trace.send(command)
    queued_argc = trace.cpu.mem[0x073B]
    if schedule == 'mailbox_before_F0':
        receive_pending(trace, mailbox_value)
    trace.send(b'\xF0')
    planted_source = trace.cpu.mem[0x07E7]
    if schedule == 'mailbox_after_F0':
        receive_pending(trace, mailbox_value)
    elif schedule not in ('mailbox_before_F0', 'no_pending_mailbox'):
        raise ValueError('unknown schedule')
    source_at_builder = trace.cpu.mem[0x07E7]
    trace.build_frame_payload()
    byte_written = trace.cpu.mem[target]
    stores = [store for store in trace.cpu.stores if store.pc == 0x9B5E]
    if not stores:
        raise AssertionError('candidate did not reach downstream store')
    applied = None
    if target == 0x0770:
        trace.apply_native_fuel()
        applied = [trace.cpu.mem[0x0730], trace.cpu.mem[0x0731]]
    return {
        'schedule': schedule, 'target': target, 'desired_value': value,
        'mailbox_test_byte': mailbox_value, 'stored_C9_argc': queued_argc,
        'total_wire_argument_bytes': 42 if prefix else 40, 'command_hex': command.hex(' '),
        'echo_hex': echoes.hex(' '), 'source_after_plant': planted_source,
        'source_at_builder': source_at_builder, 'actual_write': byte_written,
        'writer_pc': stores[-1].pc, 'writer_destination': stores[-1].address,
        'applied_fuel_alphas_in_model': applied,
        'hardware_reliability_established': False,
    }


def direct_mode_findings():
    rejected = ConsultTrace()
    rejected_echo = rejected.send(bytes([0x0A, 2, 0x81]))
    valid = ConsultTrace()
    valid_echo = valid.send(bytes([0x0A, 2, 0x82]))
    pointer_before_c9 = valid.cpu.read(0x07A0, 2)
    valid.send(c9_command(conditional_payload(0x07A0, 0x67)))
    queued_argc = valid.cpu.mem[0x073B]
    valid.send(b'\xF0')
    first = len(valid.cpu.executed)
    valid.build_frame_payload()
    frame_pcs = valid.cpu.executed[first:]
    pointer_after_plant = valid.cpu.read(0x07A0, 2)
    valid.send(b'\x30')
    valid.send(bytes([0x0A, 2, 0x82]))
    pointer_after_setup = valid.cpu.read(0x07A0, 2)
    return {
        'old_setup_hex': '0a 02 81', 'old_setup_echo_hex': rejected_echo.hex(' '),
        'accepted_setup_hex': '0a 02 82', 'accepted_setup_echo_hex': valid_echo.hex(' '),
        'C9_argc_after_direct_setup_and_20_C9_addresses': queued_argc,
        'pointer_after_valid_direct_setup': pointer_before_c9,
        'pointer_after_conditional_plant': pointer_after_plant,
        'direct_reader_executed_in_C9_frame': 0x9CDD in frame_pcs,
        'C9_reader_executed_in_C9_frame': 0x9AEB in frame_pcs,
        'pointer_after_next_direct_setup': pointer_after_setup,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    cases = [schedule_case(schedule, target) for target in (0x0770, 0x07A0)
             for schedule in ('no_pending_mailbox', 'mailbox_before_F0', 'mailbox_after_F0')]
    result = {'evidence': 'offline selected ROM paths; explicit synthetic ordering; no hardware execution',
              'direct_mode_findings': direct_mode_findings(), 'schedule_cases': cases}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
