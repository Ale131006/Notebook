# vgraphicsscene.py (Version 2)
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtGui import QWheelEvent
from PySide6.QtCore import Qt

class ViewGraphicsScene(QGraphicsScene):
    def __init__(self, main_window):
        super().__init__()
        
        self.main_window = main_window

    def wheelEvent(self, event: QWheelEvent):
        # Zoom only when Ctrl held
        if not event.modifiers() & Qt.ControlModifier:
            super().wheelEvent(event)
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self.main_window.zoom_in()
        else:
            self.main_window.zoom_out()
        event.accept()
