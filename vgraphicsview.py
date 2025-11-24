from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt, QPointF

class ViewGraphicsView(QGraphicsView):
    def __init__(self, scene, width=5000, height=5000, parent=None):
        super().__init__(scene, parent)

        self._panning = False
        self._pan_start = None

        self.setSceneRect(0, 0, width, height)
        self.ensureVisible(0, 0, 1, 1)

        # Scrollbars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.horizontalScrollBar().setValue(self.horizontalScrollBar().minimum())
        self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())



        # Zoom-Limits
        self._min_scale = 0.1    # 10%
        self._max_scale = 2.0    # 200% (entspricht 5000px, abhängig von Scene-Größe)


    # --- PAN ---
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x() * 1
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y() * 1
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


    def wheelEvent(self, event):
        # Zoom mit STRG + Mausrad
        if event.modifiers() & Qt.ControlModifier:
            zoomInFactor = 1.15
            zoomOutFactor = 1 / zoomInFactor

            current_scale = self.transform().m11()  # aktuelle Skalierung (x-Achse)
            if event.angleDelta().y() > 0:
                factor = zoomInFactor
            else:
                factor = zoomOutFactor

            new_scale = current_scale * factor

            # Limit prüfen
            if new_scale < self._min_scale:
                factor = self._min_scale / current_scale
            elif new_scale > self._max_scale:
                factor = self._max_scale / current_scale

            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)
