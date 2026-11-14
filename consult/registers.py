"""Engine ECU live-data registers with known scaling (CONSULT_PROTOCOL.md §6).

Each entry: name -> (register bytes, formula on the raw value, unit).
Multi-byte values list MSB first.

1998 Maxima (ID ED, 23710-2L904), from the 2026-11-14 reg-scan: 17 (AAC) is not
supported. 08 (coolant) echoes but won't stream on its own (F0 → FE); it does stream
alongside other registers.

Bit maps seen on that car (bit 7 = MSB; see CAR_TEST_CHECKLIST.md 3.17–3.20):
  13: b4 A/C switch, b3 power steering, b2 neutral (1 = N), b5 rear defrost load,
      b0 closed throttle
  1E: b6 fuel pump relay (probably), b1 + b7 on with A/C (relay and fan, order unknown)
  1F: b0 briefly on a throttle blip
  21: b7 / b6 O2 rich/lean per bank
"""

ENGINE = {
    "rpm":      ((0x00, 0x01), lambda v: v * 12.5, "rpm"),
    "cas_rpm":  ((0x02, 0x03), lambda v: v * 8, "rpm"),
    "maf":      ((0x04, 0x05), lambda v: v * 5, "mV"),
    "coolant":  ((0x08,), lambda v: v - 50, "°C"),
    "o2_lh":    ((0x09,), lambda v: v * 10, "mV"),
    "o2_rh":    ((0x0A,), lambda v: v * 10, "mV"),
    "speed":    ((0x0B,), lambda v: v * 2, "km/h"),
    "battery":  ((0x0C,), lambda v: v * 80 / 1000, "V"),
    "tps":      ((0x0D,), lambda v: v * 20, "mV"),
    "iat":      ((0x11,), lambda v: v - 50, "°C"),
    "bits13":   ((0x13,), lambda v: f"{v:08b}", ""),
    "inj_lh":   ((0x14, 0x15), lambda v: v / 100, "ms"),
    "inj_rh":   ((0x22, 0x23), lambda v: v / 100, "ms"),
    "timing":   ((0x16,), lambda v: 110 - v, "°BTDC"),
    "aac":      ((0x17,), lambda v: v / 2, "%"),          # not on the 1998 Maxima
    "alpha_lh": ((0x1A,), lambda v: v, "%"),
    "alpha_rh": ((0x1B,), lambda v: v, "%"),
    "bits1e":   ((0x1E,), lambda v: f"{v:08b}", ""),
    "bits1f":   ((0x1F,), lambda v: f"{v:08b}", ""),
    "bits20":   ((0x20,), lambda v: f"{v:08b}", ""),
    "bits21":   ((0x21,), lambda v: f"{v:08b}", ""),
}


def decode(names, data):
    """Turn a frame (in request order) into {name: (value, unit)}."""
    out, i = {}, 0
    for name in names:
        regs, fn, unit = ENGINE[name]
        raw = 0
        for b in data[i:i + len(regs)]:
            raw = (raw << 8) | b
        out[name] = (fn(raw), unit)
        i += len(regs)
    return out


def registers_for(names):
    return [r for name in names for r in ENGINE[name][0]]
