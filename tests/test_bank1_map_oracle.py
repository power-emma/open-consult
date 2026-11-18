from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from bank1_map_oracle import fit, interval, serialise_grid, weights


class Bank1MapOracleTests(unittest.TestCase):
    def setUp(self):
        self.axis = list(range(0, 160, 10))

    def test_interval_clamps_and_interpolates(self):
        self.assertEqual(interval(self.axis, -1), (0, 0.0))
        self.assertEqual(interval(self.axis, 155), (14, 1.0))
        self.assertEqual(interval(self.axis, 25), (2, 0.5))

    def test_weights_are_bilinear_and_normalized(self):
        result = weights(self.axis, self.axis, 25, 35)
        self.assertAlmostEqual(float(result.sum()), 1.0)
        self.assertEqual(np.flatnonzero(result).tolist(), [35, 36, 51, 52])
        self.assertTrue(np.allclose(result[np.flatnonzero(result)], 0.25))

    def test_fit_recovers_observed_nodes_and_leaves_others_unknown(self):
        samples = []
        for row in range(3):
            for col in range(4):
                samples.append((self.axis[row], self.axis[col], row * 20 + col, 5))
        result = fit(samples, self.axis, self.axis, divisor=1, ridge=0)
        grid, support = serialise_grid(result["solution"], result["support"], 1)
        for row in range(3):
            for col in range(4):
                self.assertAlmostEqual(grid[row][col], row * 20 + col, places=5)
                self.assertGreaterEqual(support[row][col], 1)
        self.assertIsNone(grid[10][10])


if __name__ == "__main__":
    unittest.main()
