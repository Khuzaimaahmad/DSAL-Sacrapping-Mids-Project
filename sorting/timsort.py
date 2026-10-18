"""Python Timsort (built-in list.sort) - O(n log n) worst, O(n) best, stable.

The built-in sort does not expose comparison / swap counts, so the stats are
set to None (shown as "n/a" in the UI).
"""
from operator import itemgetter

NAME = "Python Timsort"
COMPLEXITY = "O(n log n) worst; O(n) best"
STABLE = "Yes"


def sort(arr, cmp, stats, descending=False):
    arr.sort(key=itemgetter(0), reverse=descending)
    stats["comparisons"] = None
    stats["swaps"] = None
    return arr
