"""Insertion Sort - O(n^2), stable.

Builds the sorted part one item at a time by shifting larger items right.
"""

NAME = "Insertion Sort"
COMPLEXITY = "O(n^2)"
STABLE = "Yes"


def sort(arr, cmp, stats, descending=False):
    for i in range(1, len(arr)):
        item = arr[i]
        j = i - 1
        while j >= 0 and cmp(arr[j], item) > 0:
            arr[j + 1] = arr[j]
            stats["swaps"] += 1         # shifts count as moves
            j -= 1
        arr[j + 1] = item
    return arr
