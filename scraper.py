"""Background workers: CSV loader and a generic task runner."""
import csv
from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal

# Kaggle CSVs sometimes contain very large text fields.
csv.field_size_limit(2**31 - 1)


class CSVWorker(QThread):
    columns_ready = pyqtSignal(list)
    batch_ready = pyqtSignal(list)
    progress_changed = pyqtSignal(int, int)
    finished_loading = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, file_path, batch_size=1000):
        super().__init__()
        self.file_path = file_path
        self.batch_size = batch_size
        self.pause_event = Event()
        self.pause_event.set()          # set = running
        self.stop_event = Event()
        self.total_rows = 0

    def pause(self):
        self.pause_event.clear()

    def resume(self):
        self.pause_event.set()

    def stop(self):
        self.stop_event.set()
        self.pause_event.set()          # wake a paused worker so it can stop

    def _open(self):
        return open(self.file_path, "r", encoding="utf-8-sig",
                    errors="replace", newline="")

    def run(self):
        try:
            with self._open() as f:
                self.total_rows = max(sum(1 for _ in f) - 1, 0)

            loaded = 0
            batch = []

            with self._open() as f:
                reader = csv.DictReader(f, restval="")
                if not reader.fieldnames:
                    self.error_occurred.emit("The CSV file is empty or has no header row.")
                    return
                self.columns_ready.emit(list(reader.fieldnames))

                for row in reader:
                    while not self.pause_event.is_set() and not self.stop_event.is_set():
                        self.msleep(100)
                    if self.stop_event.is_set():
                        break

                    # Drop extra cells (key None) and fully empty rows.
                    row.pop(None, None)
                    if not any(v not in (None, "") for v in row.values()):
                        continue

                    batch.append(row)
                    loaded += 1

                    if len(batch) >= self.batch_size:
                        self.batch_ready.emit(batch)
                        batch = []
                        self.progress_changed.emit(loaded, self.total_rows)
                        self.msleep(5)  # let the UI thread breathe

                if batch:
                    self.batch_ready.emit(batch)

            self.progress_changed.emit(loaded, self.total_rows)
            word = "Stopped" if self.stop_event.is_set() else "Finished"
            self.finished_loading.emit(f"{word}. Loaded {loaded:,} records.")

        except Exception as exc:
            self.error_occurred.emit(str(exc))


class TaskWorker(QThread):
    """Runs any function off the UI thread (used for sorting / benchmark)."""
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            self.result_ready.emit(self.func(*self.args))
        except Exception as exc:
            self.error_occurred.emit(str(exc))
