from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QPen, QBrush, QFont, QAction, QIcon, QUndoStack
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsItem, QGraphicsView, QGraphicsScene,
    QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QInputDialog,
    QToolBar, QMenu, QMessageBox, QColorDialog
)
from vgraphicsscene import ViewGraphicsScene
from vgraphicsview import ViewGraphicsView
import datetime
import notify


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.drawing_enabled = False
        self.current_scene = None
        self.setWindowTitle("Smartbook")
        self.setMinimumSize(1000, 700)
        self.undo_stack = QUndoStack(self)

        # ---------------------------------
        # TOOLBAR OBEN
        # ---------------------------------
        toolbar = QToolBar("Werkzeuge")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setStyleSheet("QToolButton { padding: 6px; }")
        self.addToolBar(toolbar)

        # Zeichnen an/aus
        self.action_draw = QAction("✏️", self)
        self.action_draw.setCheckable(True)
        self.action_draw.triggered.connect(self.toggle_draw_mode)
        toolbar.addAction(self.action_draw)

        # Farbwähler
        self.action_color = QAction("🎨", self)
        self.action_color.triggered.connect(self.choose_color)
        toolbar.addAction(self.action_color)

        # Strichstärke
        self.action_thickness = QAction("➕", self)
        self.action_thickness.triggered.connect(self.choose_thickness)
        toolbar.addAction(self.action_thickness)

        # Radierer
        self.action_eraser = QAction("🧽", self)
        self.action_eraser.setCheckable(True)
        self.action_eraser.triggered.connect(self.toggle_eraser)
        toolbar.addAction(self.action_eraser)

        # Undo / Redo
        act_undo = QAction("↩️ Undo", self)
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(self.undo_stack.undo)
        toolbar.addAction(act_undo)

        act_redo = QAction("↪️ Redo", self)
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(self.undo_stack.redo)
        toolbar.addAction(act_redo)

        # ---------------------------------
        # SIDEBAR + CANVAS LAYOUT
        # ---------------------------------
        central = QWidget()
        layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        # Sidebar
        sidebar = QVBoxLayout()
        self.btn_add = QPushButton("+ Neues Notizbuch")
        self.btn_add.clicked.connect(self.add_notebook)
        sidebar.addWidget(self.btn_add)

        self.list_notebooks = QListWidget()
        self.list_notebooks.currentRowChanged.connect(self.switch_notebook)
        sidebar.addWidget(self.list_notebooks)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)

        # Canvas
        self.view = ViewGraphicsView(None)
        layout.addWidget(sidebar_widget, 1)
        layout.addWidget(self.view, 5)

        self.list_notebooks.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_notebooks.customContextMenuRequested.connect(
            self.open_notebook_context_menu
        )

        # Notizbuch-Speicher
        self.notebooks = []

        # deadline timer: check every second for visual update and notifications
        self.deadline_timer = QTimer(self)
        self.deadline_timer.setInterval(1000)  # 1 second
        self.deadline_timer.timeout.connect(self._check_deadlines)
        self.deadline_timer.start()

        # Deadline timer: prüft jede Sekunde auf Vorwarnungen / Ablauf
        self._deadline_timer = QTimer(self)
        self._deadline_timer.setInterval(1000)  # 1s
        self._deadline_timer.timeout.connect(self._check_deadlines)
        self._deadline_timer.start()

        
        # Paste (Ctrl+V)
        act_paste = QAction("Paste", self)
        act_paste.setShortcut("Ctrl+V")
        act_paste.triggered.connect(self._on_paste_triggered)
        toolbar.addAction(act_paste)


        # Erstes Notebook erzeugen
        self.add_notebook(initial=True)

    # ============================================================
    # NEUES NOTIZBUCH
    # ============================================================
    def add_notebook(self, initial=False):
        if initial:
            title = "Neues Notizbuch"
        else:
            title, ok = QInputDialog.getText(self, "Neues Notizbuch", "Titel:")
            if not ok or not title.strip():
                return

        scene = ViewGraphicsScene(self, width=5000, height=5000)

        # Titel-Textfeld im Canvas
        title_item = scene.addText(title)
        font = QFont("Arial", 28)
        font.setUnderline(True)
        title_item.setFont(font)
        title_item.setDefaultTextColor(Qt.lightGray)
        title_item.setPos(20, 20)

        self.view.setScene(scene)
        self.view.centerOn(0, 0)

        self.notebooks.append({"title": title, "scene": scene, "title_item": title_item})
        self.list_notebooks.addItem(title)
        self.list_notebooks.setCurrentRow(len(self.notebooks) - 1)

    # ============================================================
    # NOTIZBUCH WECHSELN
    # ============================================================
    def switch_notebook(self, index):
        if index < 0 or index >= len(self.notebooks):
            return
        self.current_scene = self.notebooks[index]["scene"]
        self.view.setScene(self.current_scene)
        self.current_scene.set_drawing_mode(self.action_draw.isChecked())

    # ============================================================
    # CONTEXT MENU: UMBENENNEN / LÖSCHEN
    # ============================================================
    def open_notebook_context_menu(self, position):
        item = self.list_notebooks.itemAt(position)
        if not item:
            return

        menu = QMenu()
        rename = menu.addAction("Umbenennen")
        delete = menu.addAction("Löschen")
        action = menu.exec_(self.list_notebooks.mapToGlobal(position))

        if action == rename:
            self.rename_notebook(item)
        elif action == delete:
            self.delete_notebook(item)

    def rename_notebook(self, item):
        row = self.list_notebooks.row(item)
        new_title, ok = QInputDialog.getText(
            self, "Notizbuch umbenennen", "Neuer Titel:", text=item.text()
        )
        if ok and new_title.strip():
            item.setText(new_title)
            self.notebooks[row]["title"] = new_title
            title_item = self.notebooks[row]["title_item"]
            title_item.setPlainText(new_title)

    def delete_notebook(self, item):
        row = self.list_notebooks.row(item)
        if QMessageBox.question(
            self,
            "Notizbuch löschen",
            f"Soll das Notizbuch '{item.text()}' wirklich gelöscht werden?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self.list_notebooks.takeItem(row)
            del self.notebooks[row]

        if self.notebooks:
            self.list_notebooks.setCurrentRow(0)
        else:
            empty_scene = ViewGraphicsScene(self, 5000, 5000)
            self.view.setScene(empty_scene)

    # ============================================================
    # WERKZEUGE
    # ============================================================
    def toggle_draw_mode(self, enabled):
        if self.current_scene:
            self.current_scene.set_drawing_mode(enabled)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid() and self.current_scene:
            self.current_scene.set_pen_color(color)

    def choose_thickness(self):
        thickness, ok = QInputDialog.getInt(
            self, "Strichstärke", "Neue Dicke:", 3, 1, 40, 1
        )
        if ok and self.current_scene:
            self.current_scene.set_pen_width(thickness)

    def toggle_eraser(self, enabled):
        if not self.current_scene:
            return
        self.current_scene.set_eraser_mode(enabled)
        if enabled:
            self.current_scene.drawing_enabled = True

    def _check_deadlines(self):
        """Periodisch prüfen: alle Text-Items updaten und bei Ablauf / Vorwarnung benachrichtigen."""
        now = datetime.datetime.now()
        for nb in self.notebooks:
            scene = nb.get("scene")
            if not scene:
                continue
            for item in scene.items():
                # nur TextItems behandeln (duck-typing)
                if not hasattr(item, "deadline"):
                    continue

                # erzwinge Repaint (Overlay aktualisieren)
                try:
                    item.update()
                except Exception:
                    pass

                if item.deadline is None:
                    continue

                # compute pre-notify delta (use method on item)
                try:
                    pre = item._compute_pre_notify_delta()
                except Exception:
                    pre = datetime.timedelta(minutes=5)

                # Vorwarnung
                if (not getattr(item, "_deadline_pre_notified", False)
                        and now >= (item.deadline - pre)
                        and now < item.deadline):
                    # Text snippet
                    text_snippet = item.toPlainText().strip().splitlines()[0][:120]
                    title = "Erinnerung: Deadline naht"
                    message = text_snippet if text_snippet else "Notiz"
                    try:
                        notify.show_toast(title, message)
                    except Exception:
                        QMessageBox.information(self, title, message)
                    item._deadline_pre_notified = True
                    # optional: visual update already done above

                # Endgültige Notification
                if (not getattr(item, "_deadline_notified", False)
                        and now >= item.deadline):
                    text_snippet = item.toPlainText().strip().splitlines()[0][:200]
                    title = "Deadline abgelaufen"
                    message = text_snippet if text_snippet else "Notiz"
                    try:
                        notify.show_toast(title, message)
                    except Exception:
                        QMessageBox.information(self, title, message)
                    item._deadline_notified = True
                    item.update()

    def _on_paste_triggered(self):
        """Wird von Ctrl+V ausgelöst. Leitet an aktuelle Scene weiter."""
        if not self.current_scene:
            # falls noch kein Notebook, versuche view.scene()
            scene = self.view.scene()
        else:
            scene = self.current_scene
        if not scene:
            return
        scene.paste_from_clipboard(view=self.view)

