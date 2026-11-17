"""Laptop-side native fuel-feedback map (RPM x raw ECU load code)."""
from bisect import bisect_right
import math


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class FuelMap:
    """Bilinear lookup, rounded to the native whole-percent parameter.

    Rows follow load_code_axis, columns follow rpm_axis. A null corner with
    positive interpolation weight means normal ECU control, not fixed 100%.
    Axis boundaries clamp to the nearest edge; there is no extrapolation.
    """
    def __init__(self, document):
        if not isinstance(document, dict):
            raise ValueError('fuel map must be a JSON object')
        self.rpm = self._axis(document.get('rpm_axis'), 'rpm_axis', 0, 100000)
        self.load = self._axis(document.get('load_code_axis'), 'load_code_axis', 0, 65535)
        rows = document.get('fuel_percent')
        if not isinstance(rows, list) or len(rows) != len(self.load):
            raise ValueError('fuel_percent must have one row per load_code_axis value')
        for row in rows:
            if not isinstance(row, list) or len(row) != len(self.rpm):
                raise ValueError('each fuel_percent row must have one cell per rpm_axis value')
            if any(value is not None and (not finite_number(value) or not 75 <= value <= 125) for value in row):
                raise ValueError('fuel cells must be null or finite percentages in 75..125')
        self.rows = [list(row) for row in rows]

    @staticmethod
    def _axis(axis, name, low, high):
        if not isinstance(axis, list) or len(axis) < 2:
            raise ValueError(f'{name} needs at least two breakpoints')
        if any(not finite_number(value) or not low <= value <= high for value in axis):
            raise ValueError(f'{name} breakpoints must be finite numbers in {low}..{high}')
        if any(b <= a for a, b in zip(axis, axis[1:])):
            raise ValueError(f'{name} must be strictly increasing')
        return list(axis)

    @staticmethod
    def _interval(axis, value):
        value = min(axis[-1], max(axis[0], value))
        lower = min(len(axis) - 2, max(0, bisect_right(axis, value) - 1))
        return lower, (value - axis[lower]) / (axis[lower + 1] - axis[lower])

    def lookup(self, rpm, load_code):
        if not finite_number(rpm) or not finite_number(load_code):
            raise ValueError('lookup coordinates must be finite')
        x, fx = self._interval(self.rpm, rpm)
        y, fy = self._interval(self.load, load_code)
        corners = ((self.rows[y][x], (1-fx)*(1-fy)),
                   (self.rows[y][x+1], fx*(1-fy)),
                   (self.rows[y+1][x], (1-fx)*fy),
                   (self.rows[y+1][x+1], fx*fy))
        if any(value is None and weight > 0 for value, weight in corners):
            return None
        return int(math.floor(sum(value * weight for value, weight in corners if value is not None) + 0.5))

    @classmethod
    def constant(cls, percent):
        return cls({'rpm_axis': [0, 10000], 'load_code_axis': [0, 65535],
                    'fuel_percent': [[percent, percent], [percent, percent]]})
