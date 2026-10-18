"""Main window and benchmark dialog."""
import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QProgressBar, QTableView, QTableWidget, QTableWidgetItem,
    QComboBox, QLineEdit, QMessageBox, QGroupBox, QCheckBox, QHeaderView,
    QAbstractItemView, QDialog
)

from model import RecordTableModel
from scraper import CSVWorker, TaskWorker
from sorting import ALGORITHMS, QUADRATIC, QUADRATIC_LIMIT, sort_records, benchmark_all

OPERATORS = ["contains", "starts with", "ends with", "equals", "not contains"]
NO_SECOND = "(No second column)"


class BenchmarkDialog(QDialog):
    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sorting Benchmark Results")
        self.resize(900, 400)
        layout = QVBoxLayout(self)
        headers = ["Algorithm", "Time (ms)", "Comparisons", "Swaps/moves", "Complexity", "Stable"]
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for r, data in enumerate(rows):
            for c, h in enumerate(headers):
                table.setItem(r, c, QTableWidgetItem(str(data[h])))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(table)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CS200 Project 1 - CSV Dataset Explorer")
        self.resize(1250, 760)

        self.all_records = []
        self.worker = None
        self.task = None
        self.current_file = ""

        self._build_ui()
        self._connect_signals()

    # ---------- UI construction ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        file_row = QHBoxLayout()
        self.file_label = QLabel("No CSV selected")
        self.choose_button = QPushButton("Choose CSV")
        self.start_button = QPushButton("Start / Load")
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.stop_button = QPushButton("Stop")
        for b in (self.pause_button, self.resume_button, self.stop_button):
            b.setEnabled(False)
        for w in (self.choose_button, self.start_button, self.pause_button,
                  self.resume_button, self.stop_button):
            file_row.addWidget(w)
        file_row.addWidget(self.file_label, 1)
        main_layout.addLayout(file_row)

        self.progress = QProgressBar()
        main_layout.addWidget(self.progress)
        self.status_label = QLabel("Choose a Kaggle CSV file to begin.")
        main_layout.addWidget(self.status_label)

        # Filters
        search_box = QGroupBox("Search and Filters")
        sl = QVBoxLayout(search_box)

        f1 = QHBoxLayout()
        self.column1 = QComboBox()
        self.operator1 = QComboBox(); self.operator1.addItems(OPERATORS)
        self.value1 = QLineEdit(); self.value1.setPlaceholderText("First filter value")
        for w in (QLabel("Column 1"), self.column1, self.operator1):
            f1.addWidget(w)
        f1.addWidget(self.value1, 1)
        sl.addLayout(f1)

        f2 = QHBoxLayout()
        self.logic = QComboBox(); self.logic.addItems(["AND", "OR", "NOT (filter 1)"])
        self.column2 = QComboBox()
        self.operator2 = QComboBox(); self.operator2.addItems(OPERATORS)
        self.value2 = QLineEdit(); self.value2.setPlaceholderText("Second filter value")
        for w in (QLabel("Combine"), self.logic, QLabel("Column 2"), self.column2, self.operator2):
            f2.addWidget(w)
        f2.addWidget(self.value2, 1)
        sl.addLayout(f2)

        fb = QHBoxLayout()
        self.apply_filter_button = QPushButton("Apply Filters")
        self.clear_filter_button = QPushButton("Clear Filters")
        self.result_count = QLabel("0 records")
        for w in (self.apply_filter_button, self.clear_filter_button, self.result_count):
            fb.addWidget(w)
        sl.addLayout(fb)
        main_layout.addWidget(search_box)

        # Sorting
        sort_box = QGroupBox("Sorting and Benchmark")
        sort_layout = QHBoxLayout(sort_box)
        self.sort_column = QComboBox()
        self.sort_algorithm = QComboBox(); self.sort_algorithm.addItems(list(ALGORITHMS))
        self.second_sort_column = QComboBox(); self.second_sort_column.addItem(NO_SECOND)
        self.descending = QCheckBox("Descending")
        self.filtered_scope = QCheckBox("Sort only filtered results")
        self.sort_button = QPushButton("Sort")
        self.benchmark_button = QPushButton("Benchmark All")
        for w in (QLabel("Primary column"), self.sort_column, QLabel("Algorithm"),
                  self.sort_algorithm, QLabel("Then by"), self.second_sort_column,
                  self.descending, self.filtered_scope, self.sort_button,
                  self.benchmark_button):
            sort_layout.addWidget(w)
        main_layout.addWidget(sort_box)

        self.metrics_label = QLabel("Sorting metrics will appear here.")
        self.metrics_label.setWordWrap(True)
        main_layout.addWidget(self.metrics_label)

        # Table (model/view = virtual rows, no freezing)
        self.model = RecordTableModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)   # ResizeToContents scans all rows
        header.setDefaultSectionSize(150)
        header.setStretchLastSection(True)
        vh = self.table.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.Fixed)
        vh.setDefaultSectionSize(24)
        main_layout.addWidget(self.table, 1)

    def _connect_signals(self):
        self.choose_button.clicked.connect(self.choose_csv)
        self.start_button.clicked.connect(self.start_loading)
        self.pause_button.clicked.connect(self.pause_loading)
        self.resume_button.clicked.connect(self.resume_loading)
        self.stop_button.clicked.connect(self.stop_loading)
        self.apply_filter_button.clicked.connect(self.apply_filters)
        self.clear_filter_button.clicked.connect(self.clear_filters)
        self.sort_button.clicked.connect(self.sort_data)
        self.benchmark_button.clicked.connect(self.run_benchmark)

    # ---------- helpers ----------
    def update_counts(self):
        self.result_count.setText(
            f"{len(self.model.records):,} records shown / {len(self.all_records):,} total")

    def _loading(self):
        return self.worker is not None and self.worker.isRunning()

    def _set_busy(self, busy):
        for b in (self.sort_button, self.benchmark_button,
                  self.apply_filter_button, self.clear_filter_button):
            b.setEnabled(not busy)

    def _second_column(self):
        second = self.second_sort_column.currentText()
        return None if second in (NO_SECOND, self.sort_column.currentText()) else second

    # ---------- loading ----------
    def choose_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Kaggle CSV", "", "CSV files (*.csv);;All files (*.*)")
        if path:
            self.current_file = path
            self.file_label.setText(os.path.basename(path))
            self.status_label.setText("CSV selected. Click Start / Load.")

    def start_loading(self):
        if not self.current_file:
            self.choose_csv()
            if not self.current_file:
                return
        if self._loading():
            QMessageBox.information(self, "Loading", "A CSV is already loading.")
            return

        self.all_records = []
        self.model.set_columns([])
        self.progress.setValue(0)
        self.update_counts()

        self.worker = CSVWorker(self.current_file)
        self.worker.columns_ready.connect(self.set_columns)
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

    def set_columns(self, columns):
        self.model.set_columns(columns)
        for combo in (self.column1, self.column2, self.sort_column):
            combo.clear()
            combo.addItems(columns)
        self.second_sort_column.clear()
        self.second_sort_column.addItem(NO_SECOND)
        self.second_sort_column.addItems(columns)

    def add_batch(self, batch):
        self.all_records.extend(batch)
        self.model.append_records(batch)      # cheap: only appends new rows
        self.update_counts()

    def update_progress(self, loaded, total):
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(min(loaded, max(total, 1)))
        self.status_label.setText(f"Loaded {loaded:,} of {total:,} CSV rows")

    def _loading_done_buttons(self):
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def loading_finished(self, message):
        self._loading_done_buttons()
        self.apply_filters()
        self.status_label.setText(message)

    def loading_error(self, message):
        self._loading_done_buttons()
        QMessageBox.critical(self, "CSV loading error", message)

    def pause_loading(self):
        if self._loading():
            self.worker.pause()
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True)
            self.status_label.setText("Paused.")

    def resume_loading(self):
        if self._loading():
            self.worker.resume()
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(False)
            self.status_label.setText("Resuming...")

    def stop_loading(self):
        if self._loading():
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self.status_label.setText("Stopping...")

    # ---------- filtering ----------
    @staticmethod
    def matches_filter(record, column, operator, value):
        if not value:
            return True
        text = str(record.get(column, "") or "").casefold()
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
        col1, op1, val1 = self.column1.currentText(), self.operator1.currentText(), self.value1.text().strip()
        col2, op2, val2 = self.column2.currentText(), self.operator2.currentText(), self.value2.text().strip()
        logic = self.logic.currentText()

        results = []
        for record in self.all_records:
            first = self.matches_filter(record, col1, op1, val1) if val1 else None
            second = self.matches_filter(record, col2, op2, val2) if val2 else None
            active = [r for r in (first, second) if r is not None]

            if not active:
                include = True
            elif logic == "AND":
                include = all(active)
            elif logic == "OR":
                include = any(active)
            else:  # NOT (filter 1)
                include = (not first) if first is not None else True
            if include:
                results.append(record)

        self.model.set_records(results)
        self.update_counts()
        self.status_label.setText(f"Filters applied: {len(results):,} matching records.")

    def clear_filters(self):
        self.value1.clear()
        self.value2.clear()
        self.model.set_records(list(self.all_records))
        self.update_counts()
        self.status_label.setText("Filters cleared.")

    # ---------- sorting (runs in a thread) ----------
    def _ready_for_task(self):
        if self._loading():
            QMessageBox.information(self, "Loading", "Wait for loading to finish (or press Stop).")
            return False
        if self.task is not None and self.task.isRunning():
            return False
        if not self.all_records:
            QMessageBox.information(self, "No data", "Load a CSV file first.")
            return False
        return True

    def _target(self):
        return list(self.model.records) if self.filtered_scope.isChecked() else list(self.all_records)

    def sort_data(self):
        if not self._ready_for_task():
            return
        column = self.sort_column.currentText()
        algorithm = self.sort_algorithm.currentText()
        target = self._target()

        if algorithm in QUADRATIC and len(target) > QUADRATIC_LIMIT:
            answer = QMessageBox.question(
                self, "Slow algorithm",
                f"{algorithm} is O(n^2) and you have {len(target):,} rows. "
                "It may take many minutes. Continue?")
            if answer != QMessageBox.Yes:
                return

        self._sort_ctx = (column, algorithm, self.filtered_scope.isChecked())
        self._set_busy(True)
        self.status_label.setText(f"Sorting with {algorithm}...")
        self.task = TaskWorker(sort_records, target, column, algorithm,
                               self.descending.isChecked(), self._second_column())
        self.task.result_ready.connect(self.sort_finished)
        self.task.error_occurred.connect(self.task_error)
        self.task.start()

    def sort_finished(self, result):
        sorted_records, elapsed, comparisons, swaps = result
        column, algorithm, filtered_only = self._sort_ctx
        if filtered_only:
            self.model.set_records(sorted_records)
            self.update_counts()
        else:
            self.all_records = sorted_records
            self.apply_filters()
        self._set_busy(False)

        complexity, stable = ALGORITHMS[algorithm]
        comps = "n/a" if comparisons is None else f"{comparisons:,}"
        sw = "n/a" if swaps is None else f"{swaps:,}"
        self.metrics_label.setText(
            f"Algorithm: {algorithm} | Column: {column} | Time: {elapsed:.3f} ms | "
            f"Comparisons: {comps} | Swaps/moves: {sw} | "
            f"Complexity: {complexity} | Stable: {stable}")
        self.status_label.setText("Sorting completed.")

    def run_benchmark(self):
        if not self._ready_for_task():
            return
        self._set_busy(True)
        self.status_label.setText("Benchmark running... large datasets may take time.")
        self.task = TaskWorker(benchmark_all, self._target(), self.sort_column.currentText(),
                               self.descending.isChecked(), self._second_column())
        self.task.result_ready.connect(self.benchmark_finished)
        self.task.error_occurred.connect(self.task_error)
        self.task.start()

    def benchmark_finished(self, rows):
        self._set_busy(False)
        self.status_label.setText("Benchmark completed.")
        BenchmarkDialog(rows, self).exec_()

    def task_error(self, message):
        self._set_busy(False)
        self.status_label.setText("Task failed.")
        QMessageBox.critical(self, "Error", message)

    def closeEvent(self, event):
        if self._loading():
            self.worker.stop()
            self.worker.wait(2000)
        if self.task is not None and self.task.isRunning():
            self.task.wait(2000)
        super().closeEvent(event)
