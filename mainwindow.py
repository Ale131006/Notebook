from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPen, QBrush, QFont, QAction, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsItem, QGraphicsView, QGraphicsScene, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QInputDialog, QToolBar

from vgraphicsscene import ViewGraphicsScene
from vgraphicsview import ViewGraphicsView
from PySide6.QtWidgets import QMenu, QMessageBox, QColorDialog, QInputDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.drawing_enabled = False

        self.setWindowTitle("Smartbook")
        self.setMinimumSize(1000, 700)

        self.last_pos = None

        # ---------------------------------
        #  TOOLBAR OBEN
        # ---------------------------------
        toolbar = QToolBar("Werkzeuge")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.setIconSize(QSize(32, 32))   # Größere Icons
        toolbar.setStyleSheet("QToolButton { padding: 6px; }")  # Mehr Höhe

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

        # ---------------------------------
        #  NOTIZBUCH-SPEICHER
        # ---------------------------------
        self.notebooks = []     # Jede Scene wird hier gespeichert
        self.current_scene = None

        # ---------------------------------
        #  HAUPTLAYOUT: Sidebar + Canvas
        # ---------------------------------
        central = QWidget()
        layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        # ---------------------------------
        #  SIDEBAR LINKS
        # ---------------------------------
        sidebar = QVBoxLayout()

        # + Button für neues Notizbuch
        self.btn_add = QPushButton("+ Neues Notizbuch")
        self.btn_add.clicked.connect(self.add_notebook)
        sidebar.addWidget(self.btn_add)

        # Liste aller Notizbücher
        self.list_notebooks = QListWidget()
        self.list_notebooks.currentRowChanged.connect(self.switch_notebook)
        sidebar.addWidget(self.list_notebooks)

        # Sidebar-Widget
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)

        # ---------------------------------
        #  CANVAS-BEREICH RECHTS
        # ---------------------------------
        self.view = ViewGraphicsView(None)  # Szene wird später gesetzt

        # ---------------------------------
        #  INS LAYOUT EINBAUEN
        # ---------------------------------
        layout.addWidget(sidebar_widget, 1)
        layout.addWidget(self.view, 5)

        self.list_notebooks.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_notebooks.customContextMenuRequested.connect(self.open_notebook_context_menu)

        # ---------------------------------
        #  ERSTES STANDARD-NOTIZBUCH
        # ---------------------------------
        self.add_notebook(initial=True)

    # ============================================================
    #   NEUES NOTIZBUCH ANLEGEN
    # ============================================================

    def add_notebook(self, initial=False):
        if initial:
            title = "Neues Notizbuch"
        else:
            title, ok = QInputDialog.getText(self, "Neues Notizbuch", "Titel:")
            if not ok or title.strip() == "":
                return

        # Neue Scene
        scene = ViewGraphicsScene(self, width=5000, height=5000)

        # -------------------------------------
        # ⬅️ HIER: Titel in die Canvas setzen
        title_item = scene.addText(title)
        font = QFont("Arial", 28)
        font.setUnderline(True)  # Unterstreichen
        title_item.setFont(font)
        title_item.setDefaultTextColor(Qt.GlobalColor.lightGray)
        title_item.setPos(20, 20)  # oben links

        # Beispiel-Objekte NUR beim ersten Notebook
        if initial:
            green_pen = QPen(Qt.green, 6)
            red_pen = QPen(Qt.red, 6)
            black_pen = QPen(Qt.black, 6)
            blue_brush = QBrush(Qt.blue)

            #rect1 = scene.addRect(50, 50, 100, 100, green_pen)
            #rect2 = scene.addRect(100, 100, 100, 100, red_pen)
            #rect3 = scene.addRect(150, 150, 100, 100, black_pen, blue_brush)

            #rect1.setFlag(QGraphicsItem.ItemIsMovable)
            #rect2.setFlag(QGraphicsItem.ItemIsMovable)
            #rect3.setFlag(QGraphicsItem.ItemIsMovable)

        self.view.setScene(scene)
        self.view.centerOn(0, 0)
        self.view.ensureVisible(0, 0, 10, 10)

        # Speichern
        self.notebooks.append({"title": title, "scene": scene, "title_item": title_item})

        # Sidebar-Eintrag
        self.list_notebooks.addItem(title)

        # Auf dieses Notizbuch wechseln
        self.list_notebooks.setCurrentRow(len(self.notebooks) - 1)

    # ============================================================
    #   ZWISCHEN NOTIZBÜCHERN WECHSELN
    # ============================================================
    def switch_notebook(self, index):
        if index < 0 or index >= len(self.notebooks):
            return

        scene = self.notebooks[index]["scene"]
        self.current_scene = scene
        self.view.setScene(scene)
        scene.set_drawing_mode(self.action_draw.isChecked())

    # ============================================================
    #   OPTIONAL: Zoom-Methoden
    # ============================================================
    def zoom_in(self):
        self.view.scale(1.2, 1.2)

    def zoom_out(self):
        self.view.scale(0.8, 0.8)

    def open_notebook_context_menu(self, position):
        item = self.list_notebooks.itemAt(position)
        if item is None:
            return

        menu = QMenu()

        rename_action = menu.addAction("Umbenennen")
        delete_action = menu.addAction("Löschen")

        action = menu.exec_(self.list_notebooks.mapToGlobal(position))

        if action == rename_action:
            self.rename_notebook(item)

        elif action == delete_action:
            self.delete_notebook(item)


    def rename_notebook(self, item):
        row = self.list_notebooks.row(item)

        new_title, ok = QInputDialog.getText(
            self, "Notizbuch umbenennen", "Neuer Titel:", text=item.text()
        )

        if ok and new_title.strip():
            # Sidebar aktualisieren
            item.setText(new_title)

            # Datenstruktur aktualisieren
            self.notebooks[row]["title"] = new_title

            # Canvas-Titel aktualisieren
            title_item = self.notebooks[row].get("title_item")
            if title_item:
                title_item.setPlainText(new_title)

                # Optional: Unterstreichen
                font = title_item.font()
                font.setUnderline(True)
                title_item.setFont(font)

    def delete_notebook(self, item):
        row = self.list_notebooks.row(item)

        confirm = QMessageBox.question(
            self,
            "Notizbuch löschen",
            f"Soll das Notizbuch '{item.text()}' wirklich gelöscht werden?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # Entfernen aus Liste + Datenstruktur
            self.list_notebooks.takeItem(row)
            del self.notebooks[row]

            # Falls gelöscht → leere Szene oder Standardverhalten
            if self.notebooks:
                # Erstes Notebook anzeigen
                first_scene = self.notebooks[0]["scene"]
                self.view.setScene(first_scene)
                self.list_notebooks.setCurrentRow(0)
            else:
                # Keine Notebooks mehr → leere Szene setzen
                empty_scene = ViewGraphicsScene(self, 5000, 5000)
                self.view.setScene(empty_scene)

    def toggle_draw_mode(self, enabled):
        self.drawing_enabled = enabled

        if self.current_scene:
            self.current_scene.set_drawing_mode(enabled)

        if enabled:
            self.action_draw.setText("✏️")
        else:
            self.action_draw.setText("✏️")

    def choose_color(self):
        color = QColorDialog.getColor()

        if color.isValid() and self.current_scene:
            self.current_scene.set_pen_color(color)

    def choose_thickness(self):
        thickness, ok = QInputDialog.getInt(
            self,
            "Strichstärke",
            "Neue Dicke:",
            3,      #default value
            1,      #min
            40,     #max
            1       #step
        )

        if ok and self.current_scene:
            self.current_scene.set_pen_width(thickness)

    def toggle_eraser(self, enabled):
        if not self.current_scene:
            return

        self.current_scene.set_eraser_mode(enabled)

        if enabled:
            # Radierer = Zeichenmodus aktiv, aber NICHT action_draw umschalten!
            self.current_scene.drawing_enabled = True
        else:
            # Radierer aus → nichts ändern, user steuert den Zeichenmodus selbst
            pass