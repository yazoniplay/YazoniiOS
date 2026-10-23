"""Failing regression test for the isolated Gemini auto-fix fixture."""

import unittest

from autofix_fixture import calculate_total


class CalculateTotalTests(unittest.TestCase):
    def test_sums_values_without_an_extra_one(self):
        self.assertEqual(calculate_total([1, 2, 3]), 6)


if __name__ == "__main__":
    unittest.main()
