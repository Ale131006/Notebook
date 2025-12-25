# mainwindow.py (Version 3)
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView
from vgraphicsscene import ViewGraphicsScene

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = QMainWindow()
    w.setWindowTitle("Smartbook - V3")
    scene = ViewGraphicsScene(w, width=5000, height=5000)
    view = QGraphicsView(scene)
    w.setCentralWidget(view)
    w.resize(1000,700)
    w.show()
    sys.exit(app.exec())
