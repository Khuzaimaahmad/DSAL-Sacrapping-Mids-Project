"""Quick Sort - O(n log n) average, O(n^2) worst, not stable.

Random pivot + 3-way partition (handles many equal values) and recursion only
on the smaller side -> depth is O(log n), no RecursionError.
"""
import random

NAME = "Quick Sort"
COMPLEXITY = "O(n log n) average; O(n^2) worst"
STABLE = "No"


def sort(arr, cmp, stats, descending=False):
    def quick_sort(low, high):
        while low < high:
            pivot = arr[random.randint(low, high)]
            lt, i, gt = low, low, high
            while i <= gt:
                c = cmp(arr[i], pivot)
                if c < 0:
                    arr[lt], arr[i] = arr[i], arr[lt]
                    lt += 1; i += 1; stats["swaps"] += 1
                elif c > 0:
                    arr[i], arr[gt] = arr[gt], arr[i]
                    gt -= 1; stats["swaps"] += 1
                else:
                    i += 1
            if lt - low < high - gt:
                quick_sort(low, lt - 1)
                low = gt + 1
            else:
                quick_sort(gt + 1, high)
                high = lt - 1

    quick_sort(0, len(arr) - 1)
    return arr
