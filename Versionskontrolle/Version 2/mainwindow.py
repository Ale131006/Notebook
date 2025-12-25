# mainwindow.py (Version 2)
import sys
from PySide6.QtWidgets import QMainWindow, QApplication, QGraphicsView
from PySide6.QtGui import QPen, QBrush
from PySide6.QtCore import Qt
from vgraphicsscene import ViewGraphicsScene

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smartbook - V2")
        self.setMinimumSize(800, 600)

        self.scene = ViewGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        # sample rects
        pen = QPen(Qt.green)
        self.scene.addRect(10, 10, 50, 50, pen)

    def zoom_in(self):
        self.view.scale(1.2, 1.2)

    def zoom_out(self):
        self.view.scale(0.8, 0.8)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
