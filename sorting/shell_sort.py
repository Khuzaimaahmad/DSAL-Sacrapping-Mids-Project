"""Shell Sort - depends on gap sequence, usually not stable.

Insertion sort over shrinking gaps (n/2, n/4, ... 1).
"""

NAME = "Shell Sort"
COMPLEXITY = "Depends on gap sequence"
STABLE = "Usually no"


def sort(arr, cmp, stats, descending=False):
    n = len(arr)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            temp = arr[i]
            j = i
            while j >= gap and cmp(arr[j - gap], temp) > 0:
                arr[j] = arr[j - gap]
                stats["swaps"] += 1
                j -= gap
            arr[j] = temp
        gap //= 2
    return arr
