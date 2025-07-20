import sys
import json
from datetime import date, datetime
from pathlib import Path
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QLineEdit, QLabel, QDialog, QTextEdit, QDateEdit, QHeaderView,
    QSpinBox, QToolBar, QStatusBar, QAbstractItemView, QInputDialog
)
from PyQt6.QtGui import QPalette, QColor, QAction
from PyQt6.QtCore import Qt, QTimer

# --- Config ---
API_URL = "https://task-tracker-api-u9j1.onrender.com"
USERS = ["Aidan", "Joel"]
CATEGORIES = ["Coding", "Art", "Design", "Other"]
STATUSES = ["Inactive", "Working on it", "Testing it", "Bugged", "Stuck", "Completed"]
CONFIG_PATH = Path.home() / ".tasktracker_config.json"

# --- Theme ---
def apply_dark_theme(app):
    app.setStyle('Fusion')
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(20,20,20))
    pal.setColor(QPalette.ColorRole.Base, QColor(30,30,30))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(45,45,45))
    pal.setColor(QPalette.ColorRole.Text, QColor(240,240,240))
    pal.setColor(QPalette.ColorRole.Button, QColor(50,50,50))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(240,240,240))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(80,150,200))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(20,20,20))
    app.setPalette(pal)

# --- Add/Edit Task Dialog ---
class TaskDialog(QDialog):
    def __init__(self, parent, task=None):
        super().__init__(parent)
        self.setWindowTitle("New Task" if task is None else "Edit Task")
        self.task = task
        self.resize(400,300)
        layout = QVBoxLayout(self)
        # Name
        layout.addWidget(QLabel("Name:"))
        self.name = QLineEdit(task['name'] if task else "")
        layout.addWidget(self.name)
        # User
        layout.addWidget(QLabel("User:"))
        self.user = QComboBox(); self.user.addItems(USERS)
        if task: self.user.setCurrentText(task['user'])
        layout.addWidget(self.user)
        # Category
        layout.addWidget(QLabel("Category:"))
        self.category = QComboBox(); self.category.addItems(CATEGORIES)
        if task:
            cat = task['name'].split(']')[0].strip('[')
            if cat in CATEGORIES: self.category.setCurrentText(cat)
        layout.addWidget(self.category)
        # Due
        layout.addWidget(QLabel("Due Date:"))
        self.due = QDateEdit(task and date.fromisoformat(task['due']) or date.today())
        self.due.setCalendarPopup(True)
        layout.addWidget(self.due)
        # Status
        layout.addWidget(QLabel("Status:"))
        self.status = QComboBox(); self.status.addItems(STATUSES)
        if task: self.status.setCurrentText(task['status'])
        layout.addWidget(self.status)
        # Priority
        layout.addWidget(QLabel("Priority (1-10):"))
        self.priority = QSpinBox(); self.priority.setRange(1,10)
        if task: self.priority.setValue(task.get('priority',1))
        layout.addWidget(self.priority)
        # Description
        layout.addWidget(QLabel("Description:"))
        self.desc = QTextEdit(task.get('description','') if task else "")
        layout.addWidget(self.desc)
        # Buttons
        btns = QHBoxLayout()
        ok = QPushButton("Save"); ok.clicked.connect(self.accept); btns.addWidget(ok)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject); btns.addWidget(cancel)
        layout.addLayout(btns)

    def get_data(self):
        return {
            'name': f"[{self.category.currentText()}] {self.name.text().strip()}",
            'user': self.user.currentText(),
            'due': self.due.date().toPyDate().isoformat(),
            'status': self.status.currentText(),
            'priority': self.priority.value(),
            'description': self.desc.toPlainText().strip()
        }

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TaskTracker")
        self.resize(900,600)
        # Toolbar
        toolbar = QToolBar(); self.addToolBar(toolbar)
        add_act = QAction("New Task", self); add_act.triggered.connect(self.new_task)
        toolbar.addAction(add_act); toolbar.addSeparator()
        toolbar.addWidget(QLabel("Search:"))
        self.search = QLineEdit(); self.search.setPlaceholderText("Search...")
        self.search.textChanged.connect(self.load_tasks)
        toolbar.addWidget(self.search)
        toolbar.addWidget(QLabel("Category:"))
        self.cat_f = QComboBox(); self.cat_f.addItem("All"); self.cat_f.addItems(CATEGORIES)
        self.cat_f.currentTextChanged.connect(self.load_tasks)
        toolbar.addWidget(self.cat_f)
        toolbar.addWidget(QLabel("Status:"))
        self.status_f = QComboBox(); self.status_f.addItem("All"); self.status_f.addItems(STATUSES)
        self.status_f.currentTextChanged.connect(self.load_tasks)
        toolbar.addWidget(self.status_f)
        # Table
        self.table = QTableWidget()
        cols=["Name","User","Due","Status","Priority","Description"]
        self.table.setColumnCount(len(cols)); self.table.setHorizontalHeaderLabels(cols)
        hdr = self.table.horizontalHeader(); hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setCentralWidget(self.table)
        # Status Bar
        self.setStatusBar(QStatusBar())
        # Timer
        self.timer = QTimer(self); self.timer.timeout.connect(self.load_tasks); self.timer.start(5000)
        self.load_username(); self.load_tasks()

    def load_username(self):
        if CONFIG_PATH.exists(): return json.loads(CONFIG_PATH.read_text()).get('username')
        n,ok=QInputDialog.getText(self,"Name","Enter your name:")
        if ok and n.strip(): CONFIG_PATH.write_text(json.dumps({'username':n.strip()}))

    def new_task(self):
        dlg=TaskDialog(self)
        if dlg.exec():
            data=dlg.get_data()
            r=requests.post(f"{API_URL}/tasks",json=data)
            if r.status_code==201: self.load_tasks()
            else: self.statusBar().showMessage(f"Error: {r.text}",5000)

    def load_tasks(self):
        r=requests.get(f"{API_URL}/tasks");
        if not r.ok: return
        self.tasks=r.json(); self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        s=self.search.text().lower(); cf=self.cat_f.currentText(); sf=self.status_f.currentText()
        for t in self.tasks:
            if s and s not in t['name'].lower(): continue
            if cf!='All' and not t['name'].startswith(f"[{cf}]"): continue
            if sf!='All' and t['status']!=sf: continue
            i=self.table.rowCount(); self.table.insertRow(i)
            self.table.setItem(i,0,QTableWidgetItem(t['name']))
            self.table.setItem(i,1,QTableWidgetItem(t['user']))
            self.table.setItem(i,2,QTableWidgetItem(t['due']))
            cb=QComboBox(); cb.addItems(STATUSES); cb.setCurrentText(t['status'])
            cb.currentTextChanged.connect(lambda v,tid=t['id']: self.update_status(tid,v))
            self.table.setCellWidget(i,3,cb)
            self.table.setItem(i,4,QTableWidgetItem(str(t.get('priority',1))))
            self.table.setItem(i,5,QTableWidgetItem(t.get('description','')))

    def update_status(self,tid,st): requests.put(f"{API_URL}/tasks/{tid}/status",json={'status':st})

if __name__=='__main__':
    app=QApplication(sys.argv); apply_dark_theme(app)
    w=MainWindow(); w.show(); sys.exit(app.exec())
