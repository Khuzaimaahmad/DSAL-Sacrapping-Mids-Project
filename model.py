"""Virtual table model: only visible rows are ever drawn, so 100k+ rows are fine."""
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt


class RecordTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.columns = []
        self.records = []               # the currently *visible* records

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.records)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.isValid():
            value = self.records[index.row()].get(self.columns[index.column()], "")
            return "" if value is None else str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.columns[section] if section < len(self.columns) else None
            return section + 1
        return None

    def set_columns(self, columns):
        self.beginResetModel()
        self.columns = list(columns)
        self.records = []
        self.endResetModel()

    def append_records(self, batch):
        if not batch:
            return
        first = len(self.records)
        self.beginInsertRows(QModelIndex(), first, first + len(batch) - 1)
        self.records.extend(batch)
        self.endInsertRows()

    def set_records(self, records):
        self.beginResetModel()
        self.records = records
        self.endResetModel()
