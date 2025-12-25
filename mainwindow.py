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
import os
import json
import shutil
import uuid
import sys
from pathlib import Path
from PySide6.QtCore import QStandardPaths, QPointF
from PySide6.QtGui import QImage, QPainter, QPixmap
from canvastextitem import CanvasTextItem
# mainwindow.py (oben)
from pathlib import Path
import uuid
from database_manager import DatabaseManager
from serializer import serialize_scene, deserialize_scene



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.drawing_enabled = False
        self.current_scene = None
        self.setWindowTitle("Smartbook")
        self.setMinimumSize(1000, 700)
        self.undo_stack = QUndoStack(self)

        appdata = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        self.workspace_dir = Path(appdata) / "SmartbookWorkspace"
        self.notebooks_dir = self.workspace_dir / "notebooks"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.notebooks_dir.mkdir(parents=True, exist_ok=True)
        # DATABASE initialisieren
        db_path = self.workspace_dir / "smartbook.db"
        self.db = DatabaseManager(db_path)


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

        self.pen_width = 3              # deine normale Stiftdicke
        self._base_pen_width = self.pen_width


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


        self._import_existing_folders_to_db()
        self._load_notebooks_from_db()
        self.reset_view_to_top_left()

        # Erstes Notebook erzeugen
        #self.add_notebook(initial=True)

    
    def _load_notebooks_from_db(self):
        """Lädt gespeicherte Notebooks aus der DB; falls keine vorhanden: lege ein neues an."""
        rows = self.db.list_notebooks()
        if not rows:
            # kein Eintrag -> neues initiales Notebook (wie vorher)
            self.add_notebook(initial=True)
            # nach add_notebook speichern wir den neuen Notizbucheintrag
            nb = self.notebooks[-1]
            nb_id = nb.get("id")
            if not nb_id:
                nb_id = f"nb_{uuid.uuid4().hex}"
                nb["id"] = nb_id
            # create DB entry
            self.db.create_notebook(nb_id, nb["title"], nb["path"], "{}")
            return

        # sonst: erstelle für jeden DB-Eintrag die Scene und lade scene_data
        for r in rows:
            nb_id = r["id"]
            title = r["title"] or "Notizbuch"
            path = r["path"]
            scene_json = r.get("scene_json", "{}")
            # ensure folder exists
            Path(path).mkdir(parents=True, exist_ok=True)

            scene = ViewGraphicsScene(self, width=5000, height=5000)
            scene.setBackgroundBrush(QBrush(Qt.darkGray))
            # create title item like in add_notebook
            from PySide6.QtGui import QFont
            title_item = CanvasTextItem(title, start_edit=False)
            font = QFont("Arial", 28)
            font.setUnderline(True)
            title_item.setFont(font)
            title_item.setDefaultTextColor(Qt.lightGray)
            title_item.setPos(20, 20)
            scene.addItem(title_item)

            # deserialize scene content (if any)
            try:
                deserialize_scene(scene, scene_json, path, main_window=self)
            except Exception as e:
                print("Fehler beim Deserialisieren:", e)

            self.notebooks.append({
                "id": nb_id,
                "title": title,
                "scene": scene,
                "title_item": title_item,
                "path": path,
                "dirty": False
            })
            self.list_notebooks.addItem(title)

        # set first Notebook active
        if self.notebooks:
            self.list_notebooks.setCurrentRow(0)


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
        scene.setBackgroundBrush(QBrush(Qt.darkGray))


        # Titel als CanvasTextItem (wird von save/metadata erkannt)
        font = QFont("Arial", 28)
        font.setUnderline(True)
        title_item = CanvasTextItem(title, start_edit=False)
        title_item.setFont(font)
        title_item.setDefaultTextColor(Qt.lightGray)
        title_item.setPos(20, 20)
        scene.addItem(title_item)


        self.view.setScene(scene)
        self.view.centerOn(0, 0)


        # use UUID instead of notebook_001 to be robust
        nb_uuid = f"nb_{uuid.uuid4().hex}"
        nb_path = self.notebooks_dir / nb_uuid
        nb_path.mkdir(parents=True, exist_ok=True)

        nb = {
            "id": nb_uuid,
            "title": title,
            "scene": scene,
            "title_item": title_item,
            "path": str(nb_path),
            "dirty": True
        }
        self.notebooks.append(nb)
        self.list_notebooks.addItem(title)
        self.list_notebooks.setCurrentRow(len(self.notebooks) - 1)

        # write new notebook skeleton to DB
        try:
            self.db.create_notebook(nb_uuid, title, str(nb_path), "{}")
            nb["dirty"] = False
        except Exception as e:
            print("DB create_notebook failed:", e)

        assets_dir = Path(nb_path) / "assets" / "images"
        assets_dir.mkdir(parents=True, exist_ok=True)


    def save_notebook_for_scene(self, scene):
        """Find notebook dict, serialize scene, save canvas image & update DB."""
        # find notebook
        nb = None
        for n in self.notebooks:
            if n.get("scene") is scene:
                nb = n
                break
        if nb is None:
            return

        nb_path = Path(nb["path"])
        try:
            scene_json = serialize_scene(scene, nb_path)
            # mark not dirty after successful write
            self.db.update_notebook(nb["id"], title=nb["title"], scene_json=scene_json)
            nb["dirty"] = False
        except Exception as e:
            import traceback
            print("[save] Fehler beim Speichern des Notebooks:", e)
            traceback.print_exc()

    def _import_existing_folders_to_db(self):
        # scan notebooks_dir for subfolders that are not in DB yet
        existing_db_paths = {r["path"] for r in self.db.list_notebooks()}
        for child in self.notebooks_dir.iterdir():
            if child.is_dir() and str(child) not in existing_db_paths:
                # try to extract title from a "title.txt" or fallback to folder name
                title = child.name
                # create id
                nb_uuid = f"nb_{uuid.uuid4().hex}"
                # if folder contains a canvas.png or scene.json, optionally read them
                scene_json = "{}"
                scene_json_path = child / "scene.json"
                if scene_json_path.exists():
                    try:
                        scene_json = scene_json_path.read_text(encoding="utf-8")
                    except Exception:
                        pass
                # write db entry
                self.db.create_notebook(nb_uuid, title, str(child), scene_json)

    # ============================================================
    # NOTIZBUCH WECHSELN
    # ============================================================
    def switch_notebook(self, index):
        if index < 0 or index >= len(self.notebooks):
            return
        self.current_scene = self.notebooks[index]["scene"]
        self.view.setScene(self.current_scene)
        self.current_scene.set_drawing_mode(self.action_draw.isChecked())
        self.reset_view_to_top_left()

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
        nb = self.notebooks[row]

        new_title, ok = QInputDialog.getText(
            self,
            "Notizbuch umbenennen",
            "Neuer Titel:",
            text=nb["title"]
        )

        if not ok or not new_title.strip():
            return

        # 1️⃣ Sidebar-Text ändern
        item.setText(new_title)

        # 2️⃣ Notebook-Metadaten ändern
        nb["title"] = new_title

        # 3️⃣ Canvas-Titel ändern
        title_item = nb.get("title_item")
        if title_item:
            title_item.setPlainText(new_title)

        # 4️⃣ In DB aktualisieren
        try:
            self.db.update_notebook(
                nb["id"],
                title=new_title,
                scene_json=None  # Scene bleibt gleich
            )
        except Exception as e:
            print("DB update_notebook failed:", e)

        nb["dirty"] = False

    def delete_notebook(self, item):
        row = self.list_notebooks.row(item)
        nb = self.notebooks[row]

        title = nb["title"]
        nb_id = nb.get("id")
        nb_path = nb.get("path")

        if QMessageBox.question(
            self,
            "Notizbuch löschen",
            f"Soll das Notizbuch '{title}' wirklich gelöscht werden?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        # 1️⃣ Aus DB löschen
        if nb_id:
            try:
                self.db.delete_notebook(nb_id)
            except Exception as e:
                print("DB delete_notebook failed:", e)

        # 2️⃣ Ordner löschen
        if nb_path and os.path.exists(nb_path):
            try:
                shutil.rmtree(nb_path)
            except Exception as e:
                print("Ordner konnte nicht gelöscht werden:", e)

        # 3️⃣ Aus UI & Speicher entfernen
        self.list_notebooks.takeItem(row)
        del self.notebooks[row]

        # 4️⃣ Neues aktives Notebook setzen
        if self.notebooks:
            self.list_notebooks.setCurrentRow(0)
        else:
            empty_scene = ViewGraphicsScene(self, 5000, 5000)
            self.view.setScene(empty_scene)
            self.current_scene = None


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
            self._base_pen_width = thickness      # 🔥 WICHTIG
            self.pen_width = thickness
            self.current_scene.set_pen_width(thickness)

    def toggle_eraser(self, enabled):
        if not self.current_scene:
            return

        self.current_scene.set_eraser_mode(enabled)
        self.current_scene.drawing_enabled = True

        if enabled:
            # 🧽 Eraser = 5× normale Stiftdicke
            self.current_scene.set_pen_width(self._base_pen_width * 5)
        else:
            # ✏️ Zurück zur normalen Stiftdicke
            self.current_scene.set_pen_width(self._base_pen_width)

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
                except Exception as e:
                    import traceback
                    print("[save] ERROR in _save_canvas_image:")
                    traceback.print_exc()


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

    def closeEvent(self, event):
        # save all notebooks synchronously
        try:
            for nb in list(self.notebooks):
                scene = nb.get("scene")
                if scene:
                    self.save_notebook_for_scene(scene)
        except Exception as e:
            import traceback
            print("[save] ERROR in _save_canvas_image:")
            traceback.print_exc()

        super().closeEvent(event)

    def reset_view_to_top_left(self):
        self.view.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.view.setResizeAnchor(QGraphicsView.NoAnchor)

        self.view.resetTransform()
        self.view.centerOn(0, 0)

        self.view.horizontalScrollBar().setValue(0)
        self.view.verticalScrollBar().setValue(0)



