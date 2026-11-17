import unittest
from consult.fuel_math import bank_pulse_base, cylinder_pulse, interpolate_uniform_bytes


class FuelMathTests(unittest.TestCase):
    def test_unity_factors_preserve_quantity_and_add_offset(self):
        # Incoming sum plus correction minus C800 = 8000 (Q15 unity).
        self.assertEqual(bank_pulse_base(0xa000, 0xa800, 1234, 0x4000, 77), 1311)

    def test_first_product_saturation_returns_before_later_scaling(self):
        # A later zero multiplier cannot undo an earlier saturation branch.
        self.assertEqual(bank_pulse_base(0xc7ff, 0, 0xffff, 0, 0), 0xffff)

    def test_second_product_and_addition_saturate(self):
        self.assertEqual(bank_pulse_base(0xa000, 0xa800, 40000, 0x8000, 0), 0xffff)
        self.assertEqual(bank_pulse_base(0xa000, 0xa800, 65000, 0x4000, 1000), 0xffff)

    def test_adc_carry_is_an_explicit_input(self):
        self.assertEqual(bank_pulse_base(0xc800, 0, 0x8000, 0x4000, 0), 0)
        self.assertEqual(bank_pulse_base(0xc800, 0, 0x8000, 0x4000, 0, incoming_carry=1), 1)

    def test_cylinder_adjustments_and_skip_mask(self):
        self.assertEqual(cylinder_pulse(1000, 100, 50), 1050)
        self.assertEqual(cylinder_pulse(1000, 0xff9c, 0xffce), 950)
        self.assertEqual(cylinder_pulse(1000, 100, 50, skip_first=True), 950)

    def test_cylinder_saturates_between_operations(self):
        self.assertEqual(cylinder_pulse(65530, 100, 50), 65485)
        self.assertEqual(cylinder_pulse(10, 0xff9c, 0xffce), 50)

    def test_uniform_interpolation_clamps_and_floors_both_directions(self):
        rising = [0, 15] + [15]*14
        falling = [15, 0] + [0]*14
        self.assertEqual(interpolate_uniform_bytes(rising, 8), 7)
        self.assertEqual(interpolate_uniform_bytes(falling, 8), 7)
        self.assertEqual(interpolate_uniform_bytes(rising, 255), 15)
        self.assertEqual(interpolate_uniform_bytes([3]*8, 255), 3)
        self.assertEqual(interpolate_uniform_bytes([5]*32, 255), 5)

    def test_rejects_nonword_inputs(self):
        with self.assertRaises(ValueError):
            bank_pulse_base(-1, 0, 0, 0, 0)


if __name__ == '__main__':
    unittest.main()
