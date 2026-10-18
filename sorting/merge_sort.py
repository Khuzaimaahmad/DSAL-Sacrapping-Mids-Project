"""Merge Sort - O(n log n), stable.

Splits the list in half, sorts each half, then merges them. Returns a new list.
"""

NAME = "Merge Sort"
COMPLEXITY = "O(n log n)"
STABLE = "Yes"


def sort(arr, cmp, stats, descending=False):
    def merge_sort(seq):
        if len(seq) <= 1:
            return seq
        mid = len(seq) // 2
        left = merge_sort(seq[:mid])
        right = merge_sort(seq[mid:])
        merged = []
        i = j = 0
        while i < len(left) and j < len(right):
            if cmp(left[i], right[j]) <= 0:
                merged.append(left[i]); i += 1
            else:
                merged.append(right[j]); j += 1
            stats["swaps"] += 1
        stats["swaps"] += (len(left) - i) + (len(right) - j)
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged

    return merge_sort(arr)
