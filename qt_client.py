import sys
import json
import threading
from datetime import datetime

import requests
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QLabel, QFormLayout, QDateEdit, QSpinBox, QTextEdit,
    QMessageBox
)

API_URL = "http://127.0.0.1:8000"
CONFIG_PATH = Path.home() / ".tasktracker_config.json"
USERS = ["Aidan", "Ella", "Other"]
STATUS_OPTIONS = ["Todo", "In Progress", "Done"]
CATEGORY_OPTIONS = ["Work", "Personal", "Home", "Other"]

class FetchThread(QThread):
    fetched = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            resp = requests.get(f"{API_URL}/tasks", timeout=3)
            resp.raise_for_status()
            self.fetched.emit(resp.json())
        except Exception as e:
            self.error.emit(str(e))

class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle("Edit Task" if task else "New Task")
        form = QFormLayout(self)

        self.name = QLineEdit(self)
        self.category = QComboBox(self)
        self.category.addItems(CATEGORY_OPTIONS)
        self.user = QComboBox(self)
        self.user.addItems(USERS)
        if CONFIG_PATH.exists():
            cfg = json.loads(CONFIG_PATH.read_text())
            self.user.setCurrentText(cfg.get('username', USERS[0]))
        self.due = QDateEdit(self)
        self.due.setCalendarPopup(True)
        self.status = QComboBox(self)
        self.status.addItems(STATUS_OPTIONS)
        self.priority = QSpinBox(self)
        self.priority.setRange(0, 10)
        self.description = QTextEdit(self)

        form.addRow("Name:", self.name)
        form.addRow("Category:", self.category)
        form.addRow("User:", self.user)
        form.addRow("Due:", self.due)
        form.addRow("Status:", self.status)
        form.addRow("Priority:", self.priority)
        form.addRow("Description:", self.description)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        if task:
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(self.delete_task)
            btn_layout.addWidget(delete_btn)
            # Pre-fill values
            self.name.setText(task['name'])
            self.category.setCurrentText(task.get('category', CATEGORY_OPTIONS[0]))
            self.user.setCurrentText(task['user'])
            self.due.setDate(datetime.fromisoformat(task['due']).date())
            self.status.setCurrentText(task['status'])
            self.priority.setValue(task.get('priority', 0))
            self.description.setPlainText(task.get('description', ''))

        form.addRow(btn_layout)

    def get_data(self):
        return {
            'name': self.name.text(),
            'category': self.category.currentText(),
            'user': self.user.currentText(),
            'due': self.due.date().toString(Qt.ISODate),
            'status': self.status.currentText(),
            'priority': self.priority.value(),
            'description': self.description.toPlainText()
        }

    def delete_task(self):
        confirm = QMessageBox.question(
            self, "Confirm Delete", "Delete this task?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            resp = requests.delete(f"{API_URL}/tasks/{self.task['id']}")
            if resp.status_code == 204:
                self.done(2)  # Custom code to indicate deletion
            else:
                QMessageBox.warning(self, "Error", "Failed to delete task.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Tracker")
        self.resize(800, 600)

        container = QWidget(self)
        layout = QVBoxLayout(container)

        # Toolbar
        toolbar = QHBoxLayout()
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search...")
        toolbar.addWidget(self.search)
        self.filter_category = QComboBox(self)
        self.filter_category.addItem("All Categories")
        self.filter_category.addItems(CATEGORY_OPTIONS)
        toolbar.addWidget(self.filter_category)
        self.filter_status = QComboBox(self)
        self.filter_status.addItem("All Statuses")
        self.filter_status.addItems(STATUS_OPTIONS)
        toolbar.addWidget(self.filter_status)
        new_btn = QPushButton("New Task")
        new_btn.clicked.connect(self.new_task)
        toolbar.addWidget(new_btn)
        layout.addLayout(toolbar)

        # Tasks table
        self.table = QTableWidget(0, 8, self)
        self.table.setHorizontalHeaderLabels([
            "Name", "Category", "User", "Due",
            "Status", "Priority", "Description", "Actions"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.cell_double_clicked)
        layout.addWidget(self.table)

        self.setCentralWidget(container)

        # Auto-refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_tasks)
        self.timer.start(5000)

        # Initial load
        self.refresh_tasks()

    def refresh_tasks(self):
        thread = FetchThread()
        thread.fetched.connect(self.populate_table)
        thread.error.connect(lambda e: print(f"Fetch error: {e}"))
        thread.start()

    def populate_table(self, tasks):
        self.table.setRowCount(0)
        for task in tasks:
            if (self.search.text() and self.search.text().lower() not in task['name'].lower()):
                continue
            if (self.filter_category.currentText() != "All Categories" and
                    task.get('category') != self.filter_category.currentText()):
                continue
            if (self.filter_status.currentText() != "All Statuses" and
                    task['status'] != self.filter_status.currentText()):
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(task['name']))
            self.table.setItem(row, 1, QTableWidgetItem(task.get('category', '')))
            self.table.setItem(row, 2, QTableWidgetItem(task['user']))
            self.table.setItem(row, 3, QTableWidgetItem(task['due']))
            self.table.setItem(row, 4, QTableWidgetItem(task['status']))
            self.table.setItem(row, 5, QTableWidgetItem(str(task.get('priority', 0))))
            self.table.setItem(row, 6, QTableWidgetItem(task.get('description', '')))

            # Actions
            actions = QWidget()
            h = QHBoxLayout(actions)
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _, t=task: self.edit_task(t))
            h.addWidget(edit_btn)
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, t=task: self.delete_task(t))
            h.addWidget(delete_btn)
            h.setContentsMargins(0, 0, 0, 0)
            actions.setLayout(h)
            self.table.setCellWidget(row, 7, actions)

    def new_task(self):
        dlg = TaskDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            requests.post(f"{API_URL}/tasks", json=data)
            self.refresh_tasks()

    def edit_task(self, task):
        dlg = TaskDialog(self, task)
        res = dlg.exec()
        if res == QDialog.DialogCode.Accepted:
            requests.put(f"{API_URL}/tasks/{task['id']}", json=dlg.get_data())
            self.refresh_tasks()
        elif res == 2:
            self.refresh_tasks()

    def delete_task(self, task):
        confirm = QMessageBox.question(
            self, "Confirm Delete", "Delete this task?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            requests.delete(f"{API_URL}/tasks/{task['id']}")
            self.refresh_tasks()

    def cell_double_clicked(self, row, col):
        task = {
            'id': int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)),
            'name': self.table.item(row, 0).text(),
            'category': self.table.item(row, 1).text(),
            'user': self.table.item(row, 2).text(),
            'due': self.table.item(row, 3).text(),
            'status': self.table.item(row, 4).text(),
            'priority': int(self.table.item(row, 5).text()),
            'description': self.table.item(row, 6).text(),
        }
        self.edit_task(task)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())