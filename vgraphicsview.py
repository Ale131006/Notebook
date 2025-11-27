from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt, QPointF, QEvent
from PySide6.QtGui import QPainter, QTabletEvent


class ViewGraphicsView(QGraphicsView):
    def __init__(self, scene, width=5000, height=5000, parent=None):
        super().__init__(scene, parent)

        # Tablet-Tracking aktivieren
        self.setAttribute(Qt.WA_TabletTracking, True)
        self.setMouseTracking(True)

        # Panning
        self._panning = False
        self._pan_start = None

        # WICHTIG: gute Qualität + flüssiges Zeichnen
        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.TextAntialiasing |
            QPainter.SmoothPixmapTransform
        )

        # Tablet-Stift aktivieren
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.viewport().setAttribute(Qt.WA_TabletTracking, True)

        # Scene Setup
        self.setSceneRect(0, 0, width, height)
        self.ensureVisible(0, 0, 1, 1)

        # Scrollbars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().minimum())
        self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())

        # Zoom-Limits
        self._min_scale = 0.1
        self._max_scale = 2.0

    # --------------------------------------------------------------
    # TABLET-EVENTS (SURFACE STIFT)
    # --------------------------------------------------------------
    def tabletEvent(self, event: QTabletEvent):
        """
        Weiterleitung direkt in die Scene.
        Dies verhindert Lag und deaktiviert Maus-Emulation.
        """
        if self.scene():
            self.scene().tabletEvent(event)
        event.accept()

    def event(self, event):
        """
        Fängt Tablet-Events ab, bevor Qt sie künstlich in Maus-Events umwandelt.
        Dadurch kein Delay und kein "Linie aus Ecke"-Bug.
        """
        t = event.type()
        if t in (QEvent.TabletPress, QEvent.TabletMove, QEvent.TabletRelease):
            self.tabletEvent(event)
            return True
        return super().event(event)

    # --------------------------------------------------------------
    # PANNING
    # --------------------------------------------------------------
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
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
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

    # --------------------------------------------------------------
    # ZOOMING
    # --------------------------------------------------------------
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            zoomInFactor = 1.15
            zoomOutFactor = 1 / zoomInFactor
            current_scale = self.transform().m11()

            if event.angleDelta().y() > 0:
                factor = zoomInFactor
            else:
                factor = zoomOutFactor

            new_scale = current_scale * factor

            # Limits
            if new_scale < self._min_scale:
                factor = self._min_scale / current_scale
            elif new_scale > self._max_scale:
                factor = self._max_scale / current_scale

            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)


# ----------------- SafeShapeMixin -----------------
from PySide6.QtGui import QPainterPath


class SafeShapeMixin:
    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path
