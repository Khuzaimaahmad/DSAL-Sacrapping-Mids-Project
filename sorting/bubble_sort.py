"""Bubble Sort - O(n^2), stable.

Repeatedly swaps adjacent items that are out of order. Stops early if a full
pass makes no swaps.
"""

NAME = "Bubble Sort"
COMPLEXITY = "O(n^2)"
STABLE = "Yes"


def sort(arr, cmp, stats, descending=False):
    n = len(arr)
    for i in range(n):
        changed = False
        for j in range(n - i - 1):
            if cmp(arr[j], arr[j + 1]) > 0:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                stats["swaps"] += 1
                changed = True
        if not changed:
            break
    return arr
