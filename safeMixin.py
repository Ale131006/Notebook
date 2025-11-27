from PySide6.QtGui import QPainterPath

class SafeShapeMixin:
    """Mixin für sichere, schnelle Shape-Erzeugung (keine QPoint/Sequence Fehler)"""
    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path
