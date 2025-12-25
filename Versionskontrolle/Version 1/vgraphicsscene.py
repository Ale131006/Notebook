# vgraphicsscene.py (Version 1)
from PySide6.QtWidgets import QGraphicsScene

class ViewGraphicsScene(QGraphicsScene):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
