"""Engine ECU live-data registers with known scaling (CONSULT_PROTOCOL.md §5).

Each entry: name -> (register bytes, formula on the raw value, unit).
Multi-byte values list MSB first.

1998 Maxima (ID ED, 23710-2L904), from the 2026-11-14 reg-scan: 17 (AAC) is not
supported. 08 (coolant) echoes but won't stream on its own (F0 → FE); it does stream
alongside other registers.

Bit maps seen on that car (bit 7 = MSB; see CAR_TEST_CHECKLIST.md 3.17–3.20 and
ROM_ANALYSIS.md §2):
  13: b4 A/C switch, b3 power steering, b2 neutral (1 = N), b5 rear defrost load,
      b0 closed throttle
  1E: b6 fuel pump relay (probably), b1 + b7 on with A/C (relay and fan, order unknown)
  1F: b0 briefly on a throttle blip
  21: b7 / b6 = 1 when O2 LH (09) / RH (0A) reads lean (< ~450 mV); b0 latches on
      after warm-up
  30: b6 + b5 together (front O2 heaters?), b4, b3, b2 (ROM)
  49: b3 = MAP/BARO switch solenoid on, b5 = off; b2 = test A2 output (ROM)

Entries marked PLMS take their scaling from the 1999 A32 notes and are unchecked here.
"""

ENGINE = {
    "rpm":      ((0x00, 0x01), lambda v: v * 12.5, "rpm"),
    "cas_rpm":  ((0x02, 0x03), lambda v: round(2_500_000 / v) if v else 0, "rpm"),  # REF period
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
    "learn_lh": ((0x1C,), lambda v: v, "%"),          # self-learn (3.16)
    "learn_rh": ((0x1D,), lambda v: v, "%"),
    "bits1e":   ((0x1E,), lambda v: f"{v:08b}", ""),
    "bits1f":   ((0x1F,), lambda v: f"{v:08b}", ""),
    "bits20":   ((0x20,), lambda v: f"{v:08b}", ""),
    "bits21":   ((0x21,), lambda v: f"{v:08b}", ""),
    "egr_temp": ((0x10,), lambda v: v * 20, "mV"),                # PLMS
    "iacv":     ((0x18,), lambda v: v, "step"),
    "purge":    ((0x29,), lambda v: v, "step"),
    "bits30":   ((0x30,), lambda v: f"{v:08b}", ""),
    "bits31":   ((0x31,), lambda v: f"{v:08b}", ""),
    "cal_ld":   ((0x33, 0x34), lambda v: round(v / 256, 1), "%"),  # PLMS
    "rear_o2":  ((0x35,), lambda v: v * 10, "mV"),                # PLMS
    "abs_tps":  ((0x37,), lambda v: round(v / 2.55, 1), "%"),     # PLMS
    "maf38":    ((0x38,), lambda v: v, ""),      # mass airflow, scale unknown (PLMS: % × 2.72 g/s)
    "bits49":   ((0x49,), lambda v: f"{v:08b}", ""),
    "map_sens": ((0x4A,), lambda v: v * 20, "mV"),                # PLMS
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
