"""Selection Sort - O(n^2), not stable.

Finds the smallest remaining item and swaps it into place.
"""

NAME = "Selection Sort"
COMPLEXITY = "O(n^2)"
STABLE = "No"


def sort(arr, cmp, stats, descending=False):
    n = len(arr)
    for i in range(n):
        best = i
        for j in range(i + 1, n):
            if cmp(arr[best], arr[j]) > 0:
                best = j
        if best != i:
            arr[i], arr[best] = arr[best], arr[i]
            stats["swaps"] += 1
    return arr
