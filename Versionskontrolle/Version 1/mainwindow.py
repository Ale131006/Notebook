# mainwindow.py (Version 1)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QBrush
from PySide6.QtWidgets import QMainWindow, QGraphicsItem, QGraphicsView

from vgraphicsscene import ViewGraphicsScene

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smartbook - V1")
        self.setMinimumSize(800, 600)

        self.scene = ViewGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        green_pen = QPen(Qt.green)
        green_pen.setWidth(6)
        red_pen = QPen(Qt.red)
        red_pen.setWidth(6)
        black_pen = QPen(Qt.black)
        black_pen.setWidth(6)
        blue_brush = QBrush(Qt.blue)

        rect1 = self.scene.addRect(50, 50, 100, 100, green_pen)
        rect2 = self.scene.addRect(100, 100, 100, 100, red_pen)
        rect3 = self.scene.addRect(150, 150, 100, 100, black_pen, blue_brush)

        rect1.setFlag(QGraphicsItem.ItemIsMovable)
        rect2.setFlag(QGraphicsItem.ItemIsMovable)
        rect3.setFlag(QGraphicsItem.ItemIsMovable)
