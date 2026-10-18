"""Heap Sort - O(n log n), not stable.

Builds a max-heap, then repeatedly moves the largest item to the end.
"""

NAME = "Heap Sort"
COMPLEXITY = "O(n log n)"
STABLE = "No"


def sort(arr, cmp, stats, descending=False):
    n = len(arr)

    def sift_down(size, root):
        while True:
            best = root
            left = 2 * root + 1
            right = left + 1
            if left < size and cmp(arr[left], arr[best]) > 0:
                best = left
            if right < size and cmp(arr[right], arr[best]) > 0:
                best = right
            if best == root:
                return
            arr[root], arr[best] = arr[best], arr[root]
            stats["swaps"] += 1
            root = best

    for i in range(n // 2 - 1, -1, -1):
        sift_down(n, i)
    for end in range(n - 1, 0, -1):
        arr[0], arr[end] = arr[end], arr[0]
        stats["swaps"] += 1
        sift_down(end, 0)
    return arr
