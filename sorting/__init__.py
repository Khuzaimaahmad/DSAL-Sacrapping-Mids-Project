"""Sorting algorithms with comparison / swap metrics.

One file per algorithm lives in this folder:
    bubble_sort.py  selection_sort.py  insertion_sort.py  merge_sort.py
    quick_sort.py   heap_sort.py       shell_sort.py      timsort.py

Each algorithm file exposes NAME, COMPLEXITY, STABLE and
sort(arr, cmp, stats, descending) -> sorted list.

To add a new algorithm: create a new file like the others and add it to
_MODULES below. The rest of the project (ui.py) imports from `sorting`
exactly as before.
"""
import time

from . import (bubble_sort, selection_sort, insertion_sort, merge_sort,
               quick_sort, heap_sort, shell_sort, timsort)

_MODULES = [bubble_sort, selection_sort, insertion_sort, merge_sort,
            quick_sort, heap_sort, shell_sort, timsort]

ALGORITHMS = {m.NAME: (m.COMPLEXITY, m.STABLE) for m in _MODULES}
_BY_NAME = {m.NAME: m for m in _MODULES}
QUADRATIC = ("Bubble Sort", "Selection Sort", "Insertion Sort")
QUADRATIC_LIMIT = 5000


def make_key(value):
    """Numbers sort numerically, text sorts case-insensitively, empty goes last.
    Gives a consistent total order even for mixed columns."""
    text = "" if value is None else str(value).strip()
    if text == "":
        return (2, 0.0, "")
    try:
        num = float(text)
        if num == num:                  # not NaN
            return (0, num, "")
    except ValueError:
        pass
    return (1, 0.0, text.casefold())


def sort_records(items, column, algorithm, descending=False, second=None):
    """Returns (sorted_records, elapsed_ms, comparisons, swaps_or_moves)."""
    if second:
        arr = [((make_key(r.get(column)), make_key(r.get(second))), r) for r in items]
    else:
        arr = [(make_key(r.get(column)), r) for r in items]

    stats = {"comparisons": 0, "swaps": 0}
    sign = -1 if descending else 1

    def cmp(a, b):
        stats["comparisons"] += 1
        ka, kb = a[0], b[0]
        return sign * ((ka > kb) - (ka < kb))

    start = time.perf_counter()
    if algorithm in _BY_NAME:
        arr = _BY_NAME[algorithm].sort(arr, cmp, stats, descending)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return [rec for _, rec in arr], elapsed_ms, stats["comparisons"], stats["swaps"]


def _fmt(n):
    return "n/a" if n is None else f"{n:,}"


def benchmark_all(target, column, descending=False, second=None):
    rows = []
    for algorithm, (complexity, stable) in ALGORITHMS.items():
        if algorithm in QUADRATIC and len(target) > QUADRATIC_LIMIT:
            rows.append({"Algorithm": algorithm,
                         "Time (ms)": f"Skipped (>{QUADRATIC_LIMIT:,} rows)",
                         "Comparisons": "-", "Swaps/moves": "-",
                         "Complexity": complexity, "Stable": stable})
            continue
        _, elapsed, comps, swaps = sort_records(target, column, algorithm, descending, second)
        rows.append({"Algorithm": algorithm, "Time (ms)": f"{elapsed:.3f}",
                     "Comparisons": _fmt(comps), "Swaps/moves": _fmt(swaps),
                     "Complexity": complexity, "Stable": stable})
    return rows
