"""Isolated regression fixture used to test Tuff's Gemini auto-fix flow.

This module is intentionally buggy; do not use it in application code.
"""


def calculate_total(values):
    """Return the sum of numeric values."""
    # TEST BUG: the extra one makes the regression test fail.
    return sum(values) + 1
