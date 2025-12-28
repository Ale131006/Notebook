from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QFont, QAction, QUndoStack, QColor, QTextCursor
from PySide6.QtWidgets import (
    QMainWindow, QGraphicsView,
    QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QInputDialog,
    QToolBar, QMenu, QMessageBox, QColorDialog, QComboBox, QSpinBox
)
from vgraphicsscene import ViewGraphicsScene
from vgraphicsview import ViewGraphicsView
import datetime
import notify
import os
import json
import shutil
import uuid
from pathlib import Path
from PySide6.QtCore import QStandardPaths, QPointF
from canvastextitem import CanvasTextItem
from pathlib import Path
import uuid
from database_manager import DatabaseManager
from serializer import serialize_scene, deserialize_scene
from PySide6.QtGui import QTextListFormat, QTextCursor



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.drawing_enabled = False
        self.current_scene = None
        self.setWindowTitle("Smartbook")
        self.setMinimumSize(1000, 700)
        #self.undo_stack = QUndoStack(self)  #UNDO (Auskommentiert wegen Fehler)

        appdata = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        self.workspace_dir = Path(appdata) / "SmartbookWorkspace"
        self.notebooks_dir = self.workspace_dir / "notebooks"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.notebooks_dir.mkdir(parents=True, exist_ok=True)
        # DATABASE initialisieren
        db_path = self.workspace_dir / "smartbook.db"
        self.db = DatabaseManager(db_path)


        # TOOLBAR OBEN
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

        self.pen_width = 3
        self._base_pen_width = self.pen_width


        # Undo / Redo
        """act_undo = QAction("↩️ Undo", self)
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(self.undo_stack.undo)
        toolbar.addAction(act_undo)

        act_redo = QAction("↪️ Redo", self)                    #UNDO (Auskommentiert wegen Fehler)
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(self.undo_stack.redo)
        toolbar.addAction(act_redo)"""

        # SIDEBAR + CANVAS LAYOUT
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

        # --- Default Text Style (wird auf neue TextItems angewendet) ---
        self.default_font_family = "Arial"
        self.default_font_size = 16
        self.default_text_color = QColor("#eeeeee")

        # -------------- Text style controls --------------
        # Font family (editable, short list + user can type to search)
        self.font_combo = QComboBox()
        self.font_combo.setEditable(True)
        fonts = ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana", "Calibri"]
        self.font_combo.addItems(fonts)
        self.font_combo.setCurrentText(self.default_font_family)
        self.font_combo.setFixedWidth(180)
        self.font_combo.currentTextChanged.connect(self._on_font_family_changed)
        toolbar.addWidget(self.font_combo)

        # Font size (6 - 72)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(self.default_font_size)
        self.font_size_spin.setFixedWidth(70)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        toolbar.addWidget(self.font_size_spin)

        # Text color picker (only for text)
        self.action_text_color = QAction("🅰️", self)
        self.action_text_color.setToolTip("Textfarbe wählen")
        self.action_text_color.triggered.connect(self._choose_text_color)
        toolbar.addAction(self.action_text_color)
        # -------------------------------------------------

        
        # Fett
        self.action_bold = QAction("B", self)
        self.action_bold.setCheckable(True)
        self.action_bold.triggered.connect(self._toggle_bold)
        toolbar.addAction(self.action_bold)

        # Kursiv
        self.action_italic = QAction("I", self)
        self.action_italic.setCheckable(True)
        self.action_italic.triggered.connect(self._toggle_italic)
        toolbar.addAction(self.action_italic)

        # Aufzählung
        self.action_bullet = QAction("•", self)
        self.action_bullet.triggered.connect(self._toggle_bullet_list)
        toolbar.addAction(self.action_bullet)

        # Nummerierung
        self.action_numbered = QAction("1.", self)
        self.action_numbered.triggered.connect(self._toggle_numbered_list)
        toolbar.addAction(self.action_numbered)

    
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
            scene.selectionChanged.connect(self._update_text_controls_from_selection)
            scene.setBackgroundBrush(QBrush(Qt.darkGray))
            # create title item like in add_notebook
            from PySide6.QtGui import QFont
            title_item = CanvasTextItem(title, start_edit=False)
            font = QFont("Arial", 28)
            font.setUnderline(True)
            title_item.setFont(font)
            title_item.setDefaultTextColor(Qt.lightGray)
            title_item.setPos(65, 65)
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


    # NEUES NOTIZBUCH
    def add_notebook(self, initial=False):
        if initial:
            title = "Neues Notizbuch"
        else:
            title, ok = QInputDialog.getText(self, "Neues Notizbuch", "Titel:")
            if not ok or not title.strip():
                return

        scene = ViewGraphicsScene(self, width=5000, height=5000)
        scene.selectionChanged.connect(self._update_text_controls_from_selection)
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
            self.db.update_notebook(nb["id"], title=nb["title"], scene_json=scene_json)
            nb["dirty"] = False
        except Exception as e:
            import traceback
            print("[save] Fehler beim Speichern des Notebooks:", e)
            traceback.print_exc()

    def _import_existing_folders_to_db(self):
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

    # NOTIZBUCH WECHSELN
    def switch_notebook(self, index):
        if index < 0 or index >= len(self.notebooks):
            return
        self.current_scene = self.notebooks[index]["scene"]
        try:
            # disconnect old (best effort)
            self.current_scene.selectionChanged.disconnect(self._update_text_controls_from_selection)
        except Exception:
            pass
        self.current_scene.selectionChanged.connect(self._update_text_controls_from_selection)
        self.view.setScene(self.current_scene)
        self.current_scene.set_drawing_mode(self.action_draw.isChecked())
        self.reset_view_to_top_left()

    # CONTEXT MENU: UMBENENNEN / LÖSCHEN
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


    # WERKZEUGE
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


    # ---------------- Text style handlers ----------------
    def _on_font_family_changed(self, family: str):
        family = family.strip()
        if not family:
            return
        self.default_font_family = family
        # Wenn ein TextItem ausgewählt, anwenden
        if self.current_scene:
            for it in self.current_scene.selectedItems():
                try:
                    from canvastextitem import CanvasTextItem
                    if isinstance(it, CanvasTextItem):
                        f = it.font()
                        f.setFamily(family)
                        it.setFont(f)
                        it.font_family = family
                        try:
                            self.current_scene.mark_dirty()
                        except Exception:
                            pass
                except Exception:
                    pass

    def _on_font_size_changed(self, size: int):
        self.default_font_size = int(size)

        if not self.current_scene:
            return

        for it in self.current_scene.selectedItems():
            if it.__class__.__name__ != "CanvasTextItem":
                continue


            cursor = it.textCursor()
            if not cursor:
                continue
            
            fmt = cursor.charFormat()
            fmt.setFontPointSize(int(size))

            if not cursor.hasSelection():
                cursor.select(QTextCursor.WordUnderCursor)

            cursor.mergeCharFormat(fmt)
            cursor.clearSelection()


            cursor.mergeCharFormat(fmt)
            cursor.clearSelection()
            it.setTextCursor(cursor)
            it.setFocus(Qt.OtherFocusReason)

            try:
                self.current_scene.mark_dirty()
            except Exception:
                pass


    def _choose_text_color(self):
        color = QColorDialog.getColor(initial=self.default_text_color, parent=self)
        if not color.isValid():
            return

        self.default_text_color = color

        if not self.current_scene:
            return

        for it in self.current_scene.selectedItems():
            if it.__class__.__name__ != "CanvasTextItem":
                continue

            cursor = it.textCursor()
            if not cursor:
                continue

            fmt = cursor.charFormat()
            fmt.setForeground(color)

            if not cursor.hasSelection():
                cursor.select(QTextCursor.WordUnderCursor)

            cursor.mergeCharFormat(fmt)

            it.setTextCursor(cursor)

            try:
                self.current_scene.mark_dirty()
            except Exception:
                pass

    def _update_text_controls_from_selection(self):
        """Wenn eine Selektion in der Scene passiert → Toolbar updaten."""
        if not self.current_scene:
            return
        sel = [i for i in self.current_scene.selectedItems() if i.__class__.__name__ == "CanvasTextItem"]
        if len(sel) == 1:
            it = sel[0]
            try:
                f = it.font()
                family = f.family()
                size = max(6, f.pointSize() or self.default_font_size)
                color = it.defaultTextColor()
                self.font_combo.blockSignals(True)
                self.font_size_spin.blockSignals(True)
                self.font_combo.setCurrentText(family)
                self.font_size_spin.setValue(size)
                self.font_combo.blockSignals(False)
                self.font_size_spin.blockSignals(False)
                if hasattr(color, "name"):
                    # set default_text_color preview to this color
                    self.default_text_color = color
            except Exception:
                pass
        else:
            # mehrere oder keine — Rückfall auf Defaults (aber Signals nicht auslösen)
            self.font_combo.blockSignals(True)
            self.font_size_spin.blockSignals(True)
            self.font_combo.setCurrentText(self.default_font_family)
            self.font_size_spin.setValue(self.default_font_size)
            self.font_combo.blockSignals(False)
            self.font_size_spin.blockSignals(False)


    def _toggle_bold(self):
        if not self.current_scene:
            return
        for it in self.current_scene.selectedItems():
            if not isinstance(it, CanvasTextItem):
                continue
            cursor = it.textCursor()
            fmt = cursor.charFormat()
            fmt.setFontWeight(QFont.Bold if not fmt.font().bold() else QFont.Normal)
            cursor.mergeCharFormat(fmt)
            it.setTextCursor(cursor)

    def _toggle_italic(self):
        if not self.current_scene:
            return
        for it in self.current_scene.selectedItems():
            if not isinstance(it, CanvasTextItem):
                continue
            cursor = it.textCursor()
            fmt = cursor.charFormat()
            fmt.setFontItalic(not fmt.fontItalic())
            cursor.mergeCharFormat(fmt)
            it.setTextCursor(cursor)

    def _toggle_bullet_list(self):
        if not self.current_scene:
            return
        for it in self.current_scene.selectedItems():
            if not isinstance(it, CanvasTextItem):
                continue
            cursor = it.textCursor()
            cursor.beginEditBlock()
            block_format = cursor.blockFormat()
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.ListDisc)
            cursor.createList(list_format)
            cursor.endEditBlock()
            it.setTextCursor(cursor)

    def _toggle_numbered_list(self):
        if not self.current_scene:
            return
        for it in self.current_scene.selectedItems():
            if not isinstance(it, CanvasTextItem):
                continue
            cursor = it.textCursor()
            cursor.beginEditBlock()
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.ListDecimal)
            cursor.createList(list_format)
            cursor.endEditBlock()
            it.setTextCursor(cursor)



