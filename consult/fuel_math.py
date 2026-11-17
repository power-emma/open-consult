"""Partial 2L904 fuel arithmetic reconstructed from 0x69F7..0x6A1F.

This models the ordinary path from a bank correction sum to its pulse base.
It does not decode factory table coefficients or predict measured AFR.
Inputs are raw RAM words, not physical units. Incoming ADC carry is explicit.
The caller must establish 16-bit mode and Y=FFFF (the observed normal caller).
"""


def word(value):
    if type(value) is not int or not 0 <= value <= 0xffff:
        raise ValueError('expected an unsigned 16-bit RAM word')
    return value


def bank_pulse_base(bank_sum, correction_0cd2, quantity_0906,
                    factor_0a58, additive_0a9c, *, incoming_carry=0):
    """Model the normal 16-bit helper path, preserving its intermediate truncation.

    ADC at 69F7 wraps rather than saturating. SEC/SBC at 69FA/69FB
    then subtracts C800 modulo 65536. Each shifted multiplication and
    the final additive correction saturate to FFFF on overflow.
    The 7700 manual specifies unsigned MPY and clears carry. Shift
    instructions establish subsequent carries; caller state remains explicit.
    """
    values = [word(v) for v in (bank_sum, correction_0cd2, quantity_0906,
                                factor_0a58, additive_0a9c)]
    if incoming_carry not in (0, 1):
        raise ValueError('carry must be 0 or 1')
    bank_sum, correction, quantity, factor, additive = values
    coefficient = ((bank_sum + correction + incoming_carry) & 0xffff)
    coefficient = (coefficient - 0xc800) & 0xffff
    first = (coefficient * quantity) >> 15
    if first > 0xffff:
        return 0xffff
    second = (first * factor) >> 14
    if second > 0xffff:
        return 0xffff
    return min(0xffff, second + additive)


def cylinder_pulse(base, first_trim_word, second_trim_word, *, skip_first=False):
    """6A3B..6A8D: apply signed add then signed subtract with saturation.

    The 0A97 cylinder mask skips only the first adjustment. The second
    adjustment is still applied. Inputs/return are raw pulse units.
    """
    base, first, second = map(word, (base, first_trim_word, second_trim_word))
    signed = lambda value: value if value < 0x8000 else value - 0x10000
    saturate = lambda value: max(0, min(0xffff, value))
    adjusted = base if skip_first else saturate(base + signed(first))
    return saturate(adjusted - signed(second))


def interpolate_uniform_bytes(table, coordinate):
    """EA77/EA82/EA8D: unsigned byte tables on a uniform 0..255 axis.

    Verified assembly entrypoints support 8, 16 or 32 entries, with spacing
    32, 16 or 8 respectively. Input clamps to the last node. Both rising
    and falling segments return the floor of linear interpolation. This
    is the readable 1D helper, not proof of the missing 2D lookup algorithm.
    """
    if len(table) not in (8, 16, 32):
        raise ValueError('expected 8, 16 or 32 entries')
    if type(coordinate) is not int or not 0 <= coordinate <= 255:
        raise ValueError('expected an unsigned byte coordinate')
    if any(type(v) is not int or not 0 <= v <= 255 for v in table):
        raise ValueError('expected byte table entries')
    step = 256 // len(table)
    coordinate = min(coordinate, step * (len(table)-1))
    i, remainder = divmod(coordinate, step)
    if not remainder:
        return table[i]
    return (table[i]*(step-remainder) + table[i+1]*remainder) // step
