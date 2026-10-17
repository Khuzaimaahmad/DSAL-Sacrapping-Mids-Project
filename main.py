import csv
import heapq
import os
import sys
import time
from functools import cmp_to_key
from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QComboBox, QLineEdit, QMessageBox, QGroupBox,
    QCheckBox, QHeaderView, QAbstractItemView
)


# -------------------- CSV LOADING WORKER --------------------

class CSVWorker(QThread):
    batch_ready = pyqtSignal(list)
    progress_changed = pyqtSignal(int, int)
    finished_loading = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, file_path, batch_size=200):
        super().__init__()
        self.file_path = file_path
        self.batch_size = batch_size
        self.pause_event = Event()
        self.pause_event.set()  # Set means running
        self.stop_event = Event()
        self.total_rows = 0

    def pause(self):
        self.pause_event.clear()

    def resume(self):
        self.pause_event.set()

    def stop(self):
        self.stop_event.set()
        self.pause_event.set()  # Let a paused worker wake up and stop

    def run(self):
        try:
            # Count rows first so the progress bar has a useful maximum.
            with open(self.file_path, "r", encoding="utf-8-sig", newline="") as f:
                self.total_rows = max(sum(1 for _ in f) - 1, 0)

            loaded = 0
            batch = []

            with open(self.file_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    self.error_occurred.emit("The CSV file is empty or has no header row.")
                    return

                for row in reader:
                    while not self.pause_event.is_set() and not self.stop_event.is_set():
                        self.msleep(100)

                    if self.stop_event.is_set():
                        break

                    # Ignore fully empty rows.
                    if not any(value not in (None, "") for value in row.values()):
                        continue

                    batch.append(row)
                    loaded += 1

                    if len(batch) >= self.batch_size:
                        self.batch_ready.emit(batch)
                        batch = []
                        self.progress_changed.emit(loaded, self.total_rows)

                if batch:
                    self.batch_ready.emit(batch)

            self.progress_changed.emit(loaded, self.total_rows)
            if self.stop_event.is_set():
                self.finished_loading.emit(f"Stopped. Loaded {loaded:,} records.")
            else:
                self.finished_loading.emit(f"Finished. Loaded {loaded:,} records.")

        except Exception as exc:
            self.error_occurred.emit(str(exc))


# -------------------- SORTING ALGORITHMS + METRICS --------------------

def compare_values(a, b):
    """Compare values naturally when both look numeric; otherwise compare text."""
    a_text = "" if a is None else str(a).strip()
    b_text = "" if b is None else str(b).strip()

    try:
        return (float(a_text) > float(b_text)) - (float(a_text) < float(b_text))
    except (ValueError, TypeError):
        a_text, b_text = a_text.casefold(), b_text.casefold()
        return (a_text > b_text) - (a_text < b_text)


def sort_records(items, column, algorithm, descending=False):
    """Return sorted records and simple comparison/swap-or-move metrics."""
    arr = list(items)
    comparisons = 0
    swaps = 0

    def greater(a, b):
        nonlocal comparisons
        comparisons += 1
        result = compare_values(a.get(column, ""), b.get(column, ""))
        return result < 0 if descending else result > 0

    start = time.perf_counter()

    if algorithm == "Bubble Sort":
        n = len(arr)
        for i in range(n):
            changed = False
            for j in range(0, n - i - 1):
                if greater(arr[j], arr[j + 1]):
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    swaps += 1
                    changed = True
            if not changed:
                break

    elif algorithm == "Selection Sort":
        for i in range(len(arr)):
            best = i
            for j in range(i + 1, len(arr)):
                if greater(arr[best], arr[j]):
                    best = j
            if best != i:
                arr[i], arr[best] = arr[best], arr[i]
                swaps += 1

    elif algorithm == "Insertion Sort":
        for i in range(1, len(arr)):
            item = arr[i]
            j = i - 1
            while j >= 0:
                comparisons += 1
                result = compare_values(arr[j].get(column, ""), item.get(column, ""))
                should_move = result < 0 if descending else result > 0
                if not should_move:
                    break
                arr[j + 1] = arr[j]
                swaps += 1  # Counts shifts as moves for this algorithm.
                j -= 1
            arr[j + 1] = item

    elif algorithm == "Merge Sort":
        def merge_sort(seq):
            nonlocal comparisons, swaps
            if len(seq) <= 1:
                return seq
            mid = len(seq) // 2
            left = merge_sort(seq[:mid])
            right = merge_sort(seq[mid:])
            merged = []
            i = j = 0
            while i < len(left) and j < len(right):
                comparisons += 1
                result = compare_values(left[i].get(column, ""), right[j].get(column, ""))
                take_left = result >= 0 if descending else result <= 0
                if take_left:
                    merged.append(left[i])
                    i += 1
                else:
                    merged.append(right[j])
                    j += 1
                swaps += 1  # Counts output moves for merge sort.
            merged.extend(left[i:])
            merged.extend(right[j:])
            swaps += len(left) - i + len(right) - j
            return merged
        arr = merge_sort(arr)

    elif algorithm == "Quick Sort":
        def quick_sort(low, high):
            nonlocal comparisons, swaps
            if low >= high:
                return
            pivot = arr[high].get(column, "")
            i = low - 1
            for j in range(low, high):
                comparisons += 1
                result = compare_values(arr[j].get(column, ""), pivot)
                belongs_left = result >= 0 if descending else result <= 0
                if belongs_left:
                    i += 1
                    if i != j:
                        arr[i], arr[j] = arr[j], arr[i]
                        swaps += 1
            if i + 1 != high:
                arr[i + 1], arr[high] = arr[high], arr[i + 1]
                swaps += 1
            quick_sort(low, i)
            quick_sort(i + 2, high)
        quick_sort(0, len(arr) - 1)

    elif algorithm == "Heap Sort":
        # Build a heap, then repeatedly move its root to the end.
        def heapify(size, root):
            nonlocal swaps
            best = root
            left = 2 * root + 1
            right = 2 * root + 2

            if left < size and greater(arr[left], arr[best]):
                best = left
            if right < size and greater(arr[right], arr[best]):
                best = right

            if best != root:
                arr[root], arr[best] = arr[best], arr[root]
                swaps += 1
                heapify(size, best)

        n = len(arr)
        for i in range(n // 2 - 1, -1, -1):
            heapify(n, i)

        for end in range(n - 1, 0, -1):
            arr[0], arr[end] = arr[end], arr[0]
            swaps += 1
            heapify(end, 0)

    elif algorithm == "Shell Sort":
        gap = len(arr) // 2
        while gap > 0:
            for i in range(gap, len(arr)):
                temp = arr[i]
                j = i
                while j >= gap:
                    comparisons += 1
                    result = compare_values(arr[j - gap].get(column, ""), temp.get(column, ""))
                    should_move = result < 0 if descending else result > 0
                    if not should_move:
                        break
                    arr[j] = arr[j - gap]
                    swaps += 1
                    j -= gap
                arr[j] = temp
            gap //= 2

    elif algorithm == "Python Timsort":
        # Python's built-in stable sort; comparisons are not exposed directly.
        def cmp_rows(a, b):
            result = compare_values(a.get(column, ""), b.get(column, ""))
            return -result if descending else result
        arr.sort(key=cmp_to_key(cmp_rows))
        comparisons = max(len(arr) - 1, 0)  # Estimate, not an exact count.
        swaps = 0  # Python does not expose its internal move count.

    elapsed_ms = (time.perf_counter() - start) * 1000
    return arr, elapsed_ms, comparisons, swaps


ALGORITHMS = {
    "Bubble Sort": ("O(n^2)", "Yes"),
    "Selection Sort": ("O(n^2)", "No"),
    "Insertion Sort": ("O(n^2)", "Yes"),
    "Merge Sort": ("O(n log n)", "Yes"),
    "Quick Sort": ("O(n log n) average; O(n^2) worst", "No"),
    "Heap Sort": ("O(n log n)", "No"),
    "Shell Sort": ("Depends on gap sequence", "Usually no"),
    "Python Timsort": ("O(n log n) worst; O(n) best", "Yes"),
}


# -------------------- MAIN WINDOW --------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CS200 Project 1 - CSV Dataset Explorer")
        self.resize(1250, 760)

        self.all_records = []
        self.visible_records = []
        self.columns = []
        self.worker = None
        self.current_file = ""

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # File controls
        file_row = QHBoxLayout()
        self.file_label = QLabel("No CSV selected")
        self.choose_button = QPushButton("Choose CSV")
        self.start_button = QPushButton("Start / Load")
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.stop_button = QPushButton("Stop")
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        for widget in [self.choose_button, self.start_button, self.pause_button,
                       self.resume_button, self.stop_button]:
            file_row.addWidget(widget)
        file_row.addWidget(self.file_label, 1)
        main_layout.addLayout(file_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        main_layout.addWidget(self.progress)
        self.status_label = QLabel("Choose a Kaggle CSV file to begin.")
        main_layout.addWidget(self.status_label)

        # Search/filter controls
        search_box = QGroupBox("Search and Filters")
        search_layout = QVBoxLayout(search_box)

        filter1 = QHBoxLayout()
        self.column1 = QComboBox()
        self.operator1 = QComboBox()
        self.operator1.addItems(["contains", "starts with", "ends with", "equals", "not contains"])
        self.value1 = QLineEdit()
        self.value1.setPlaceholderText("First filter value")
        filter1.addWidget(QLabel("Column 1"))
        filter1.addWidget(self.column1)
        filter1.addWidget(self.operator1)
        filter1.addWidget(self.value1, 1)
        search_layout.addLayout(filter1)

        filter2 = QHBoxLayout()
        self.logic = QComboBox()
        self.logic.addItems(["AND", "OR", "NOT (filter 1)"])
        self.column2 = QComboBox()
        self.operator2 = QComboBox()
        self.operator2.addItems(["contains", "starts with", "ends with", "equals", "not contains"])
        self.value2 = QLineEdit()
        self.value2.setPlaceholderText("Second filter value")
        filter2.addWidget(QLabel("Combine"))
        filter2.addWidget(self.logic)
        filter2.addWidget(QLabel("Column 2"))
        filter2.addWidget(self.column2)
        filter2.addWidget(self.operator2)
        filter2.addWidget(self.value2, 1)
        search_layout.addLayout(filter2)

        search_buttons = QHBoxLayout()
        self.apply_filter_button = QPushButton("Apply Filters")
        self.clear_filter_button = QPushButton("Clear Filters")
        self.result_count = QLabel("0 records")
        search_buttons.addWidget(self.apply_filter_button)
        search_buttons.addWidget(self.clear_filter_button)
        search_buttons.addWidget(self.result_count)
        search_layout.addLayout(search_buttons)
        main_layout.addWidget(search_box)

        # Sorting controls
        sort_box = QGroupBox("Sorting and Benchmark")
        sort_layout = QHBoxLayout(sort_box)
        self.sort_column = QComboBox()
        self.sort_algorithm = QComboBox()
        self.sort_algorithm.addItems(list(ALGORITHMS.keys()))
        self.second_sort_column = QComboBox()
        self.second_sort_column.addItem("(No second column)")
        self.descending = QCheckBox("Descending")
        self.filtered_scope = QCheckBox("Sort only filtered results")
        self.sort_button = QPushButton("Sort")
        self.benchmark_button = QPushButton("Benchmark All")
        sort_layout.addWidget(QLabel("Primary column"))
        sort_layout.addWidget(self.sort_column)
        sort_layout.addWidget(QLabel("Algorithm"))
        sort_layout.addWidget(self.sort_algorithm)
        sort_layout.addWidget(QLabel("Then by"))
        sort_layout.addWidget(self.second_sort_column)
        sort_layout.addWidget(self.descending)
        sort_layout.addWidget(self.filtered_scope)
        sort_layout.addWidget(self.sort_button)
        sort_layout.addWidget(self.benchmark_button)
        main_layout.addWidget(sort_box)

        self.metrics_label = QLabel("Sorting metrics will appear here.")
        self.metrics_label.setWordWrap(True)
        main_layout.addWidget(self.metrics_label)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table, 1)

        # Connect buttons
        self.choose_button.clicked.connect(self.choose_csv)
        self.start_button.clicked.connect(self.start_loading)
        self.pause_button.clicked.connect(self.pause_loading)
        self.resume_button.clicked.connect(self.resume_loading)
        self.stop_button.clicked.connect(self.stop_loading)
        self.apply_filter_button.clicked.connect(self.apply_filters)
        self.clear_filter_button.clicked.connect(self.clear_filters)
        self.sort_button.clicked.connect(self.sort_data)
        self.benchmark_button.clicked.connect(self.run_benchmark)

    def choose_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Kaggle CSV", "", "CSV files (*.csv);;All files (*.*)"
        )
        if path:
            self.current_file = path
            self.file_label.setText(os.path.basename(path))
            self.status_label.setText("CSV selected. Click Start / Load.")

    def start_loading(self):
        if not self.current_file:
            self.choose_csv()
            if not self.current_file:
                return

        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Loading", "A CSV is already loading.")
            return

        self.all_records = []
        self.visible_records = []
        self.columns = []
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.progress.setValue(0)
        self.result_count.setText("0 records")

        self.worker = CSVWorker(self.current_file)
        self.worker.batch_ready.connect(self.add_batch)
        self.worker.progress_changed.connect(self.update_progress)
        self.worker.finished_loading.connect(self.loading_finished)
        self.worker.error_occurred.connect(self.loading_error)
        self.worker.start()

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Loading CSV...")

    def add_batch(self, batch):
        if not batch:
            return

        if not self.columns:
            self.columns = list(batch[0].keys())
            self.table.setColumnCount(len(self.columns))
            self.table.setHorizontalHeaderLabels(self.columns)
            for combo in [self.column1, self.column2, self.sort_column]:
                combo.clear()
                combo.addItems(self.columns)
            self.second_sort_column.clear()
            self.second_sort_column.addItem("(No second column)")
            self.second_sort_column.addItems(self.columns)

        self.all_records.extend(batch)
        self.visible_records.extend(batch)
        self.render_table(self.visible_records)

    def render_table(self, records):
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(records))
        self.table.setColumnCount(len(self.columns))

        for row_index, record in enumerate(records):
            for col_index, column in enumerate(self.columns):
                value = record.get(column, "")
                item = QTableWidgetItem("" if value is None else str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

        self.table.setUpdatesEnabled(True)
        self.result_count.setText(f"{len(records):,} records shown / {len(self.all_records):,} total")

    def update_progress(self, loaded, total):
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(min(loaded, max(total, 1)))
        self.status_label.setText(f"Loaded {loaded:,} of {total:,} CSV rows")

    def loading_finished(self, message):
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.status_label.setText(message)
        self.apply_filters()

    def loading_error(self, message):
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        QMessageBox.critical(self, "CSV loading error", message)

    def pause_loading(self):
        if self.worker and self.worker.isRunning():
            self.worker.pause()
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True)
            self.status_label.setText("Paused.")

    def resume_loading(self):
        if self.worker and self.worker.isRunning():
            self.worker.resume()
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(False)
            self.status_label.setText("Resuming...")

    def stop_loading(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.status_label.setText("Stopping...")
            self.stop_button.setEnabled(False)

    def matches_filter(self, record, column, operator, value):
        if not value:
            return True
        text = str(record.get(column, "")).casefold()
        value = value.casefold()
        if operator == "contains":
            return value in text
        if operator == "starts with":
            return text.startswith(value)
        if operator == "ends with":
            return text.endswith(value)
        if operator == "equals":
            return text == value
        if operator == "not contains":
            return value not in text
        return True

    def apply_filters(self):
        if not self.all_records:
            return

        col1 = self.column1.currentText()
        op1 = self.operator1.currentText()
        val1 = self.value1.text().strip()
        col2 = self.column2.currentText()
        op2 = self.operator2.currentText()
        val2 = self.value2.text().strip()
        logic = self.logic.currentText()

        results = []
        for record in self.all_records:
            first = self.matches_filter(record, col1, op1, val1) if val1 else None
            second = self.matches_filter(record, col2, op2, val2) if val2 else None

            if first is None and second is None:
                include = True
            elif logic == "AND":
                active = [result for result in (first, second) if result is not None]
                include = all(active)
            elif logic == "OR":
                active = [result for result in (first, second) if result is not None]
                include = any(active)
            else:  # NOT (filter 1)
                include = (not first) if first is not None else True

            if include:
                results.append(record)

        self.visible_records = results
        self.render_table(self.visible_records)
        self.status_label.setText(f"Filters applied: {len(results):,} matching records.")

    def clear_filters(self):
        self.value1.clear()
        self.value2.clear()
        self.visible_records = list(self.all_records)
        self.render_table(self.visible_records)
        self.status_label.setText("Filters cleared.")

    def sort_data(self):
        if not self.visible_records:
            QMessageBox.information(self, "No data", "Load a CSV file first.")
            return

        column = self.sort_column.currentText()
        algorithm = self.sort_algorithm.currentText()
        descending = self.descending.isChecked()
        scope_filtered = self.filtered_scope.isChecked()

        second = self.second_sort_column.currentText()

        if scope_filtered:
            target = list(self.visible_records)
            # Stable-sort by the secondary key first, then apply the chosen
            # algorithm to the primary key.
            if second != "(No second column)" and second != column:
                target.sort(key=lambda row: str(row.get(second, "")).casefold(),
                            reverse=descending)
            sorted_records, elapsed, comparisons, swaps = sort_records(
                target, column, algorithm, descending
            )
            self.visible_records = sorted_records
        else:
            target = list(self.all_records)
            if second != "(No second column)" and second != column:
                target.sort(key=lambda row: str(row.get(second, "")).casefold(),
                            reverse=descending)
            sorted_records, elapsed, comparisons, swaps = sort_records(
                target, column, algorithm, descending
            )
            self.all_records = sorted_records
            self.apply_filters()

        complexity, stable = ALGORITHMS[algorithm]
        self.metrics_label.setText(
            f"Algorithm: {algorithm} | Column: {column} | "
            f"Time: {elapsed:.3f} ms | Comparisons: {comparisons:,} | "
            f"Swaps/moves: {swaps:,} | Complexity: {complexity} | Stable: {stable}"
        )
        self.status_label.setText("Sorting completed.")

    def run_benchmark(self):
        if not self.visible_records:
            QMessageBox.information(self, "No data", "Load a CSV file first.")
            return

        column = self.sort_column.currentText()
        descending = self.descending.isChecked()
        target = list(self.visible_records) if self.filtered_scope.isChecked() else list(self.all_records)

        self.status_label.setText("Benchmark running... large datasets may take time.")
        QApplication.processEvents()

        rows = []
        for algorithm, (complexity, stable) in ALGORITHMS.items():
            # Avoid freezing for quadratic algorithms on very large datasets.
            if algorithm in ("Bubble Sort", "Selection Sort", "Insertion Sort") and len(target) > 5000:
                rows.append({
                    "Algorithm": algorithm,
                    "Time (ms)": "Skipped (>5,000 rows)",
                    "Comparisons": "-",
                    "Swaps/moves": "-",
                    "Complexity": complexity,
                    "Stable": stable,
                })
                continue

            _, elapsed, comparisons, swaps = sort_records(
                target, column, algorithm, descending
            )
            rows.append({
                "Algorithm": algorithm,
                "Time (ms)": f"{elapsed:.3f}",
                "Comparisons": f"{comparisons:,}",
                "Swaps/moves": f"{swaps:,}",
                "Complexity": complexity,
                "Stable": stable,
            })

        dialog = BenchmarkWindow(rows, self)
        dialog.exec_()
        self.status_label.setText("Benchmark completed.")


class BenchmarkWindow(QMainWindow):
    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sorting Benchmark Results")
        self.resize(900, 400)

        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        table = QTableWidget(len(rows), 6)
        headers = ["Algorithm", "Time (ms)", "Comparisons", "Swaps/moves", "Complexity", "Stable"]
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        for r, data in enumerate(rows):
            for c, header in enumerate(headers):
                table.setItem(r, c, QTableWidgetItem(str(data[header])))

        layout.addWidget(table)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
