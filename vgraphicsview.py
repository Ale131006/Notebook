from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPainter, QTabletEvent, QMouseEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class ViewGraphicsView(QGraphicsView):
    def __init__(self, scene, width=5000, height=5000, parent=None):
        super().__init__(scene, parent)
        self.setViewport(QOpenGLWidget())

        # Tablet-Tracking aktivieren
        self.setAttribute(Qt.WA_TabletTracking, True)
        self.setMouseTracking(True)

        self.setAcceptDrops(True)

        # Panning
        self._panning = False
        self._pan_start = None

        # Tablet-down state (für korrekte Buttons bei Move)
        self._tablet_down = False

        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.TextAntialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)

        # Tablet-Stift aktivieren
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

        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing, True)
        self.setCacheMode(QGraphicsView.CacheBackground)
        self.setRenderHint(QPainter.Antialiasing, False)

        self._pen_active = False


    # TABLET-EVENTS (SURFACE STIFT)
    def tabletEvent(self, event: QTabletEvent):
        """
        Convert tablet events (press/move/release) into synthetic QMouseEvent and
        dispatch them via QGraphicsView.event so the scene receives normal mouse events.
        This avoids Qt's built-in tablet->mouse emulation path which can add lag.
        Pressure/tilt are ignored in this conversion (we simulate simple left-button).
        """

        self._pen_active = True

        # pick best-available local / window / screen positions
        try:
            local_pos = event.position()
        except Exception:
            try:
                local_pos = event.posF()
            except Exception:
                local_pos = event.pos()

        try:
            window_pos = event.windowPos()
        except Exception:
            window_pos = local_pos

        try:
            screen_pos = event.globalPosition()
        except Exception:
            # fallback: use window_pos as approximation
            screen_pos = window_pos

        t = event.type()
        if t == QEvent.TabletPress:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            mtype = QEvent.MouseButtonPress
            button = Qt.LeftButton
            buttons = Qt.LeftButton
            self._tablet_down = True
        elif t == QEvent.TabletMove:
            mtype = QEvent.MouseMove
            button = Qt.NoButton
            buttons = Qt.LeftButton if self._tablet_down else Qt.NoButton
        elif t == QEvent.TabletRelease:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            mtype = QEvent.MouseButtonRelease
            button = Qt.LeftButton
            buttons = Qt.NoButton
            self._tablet_down = False
        else:
            # other tablet events (e.g. proximity) -> ignore
            event.ignore()
            return
        try:
            fake = QMouseEvent(
                mtype,
                local_pos,
                window_pos,
                screen_pos,
                button,
                buttons,
                event.modifiers()
            )
        except TypeError:
            # fallback: (type, localPos, screenPos, button, buttons, modifiers)
            fake = QMouseEvent(
                mtype,
                local_pos,
                screen_pos,
                button,
                buttons,
                event.modifiers()
            )

        # Dispatch through QGraphicsView.event so normal Qt machinery creates QGraphicsSceneMouseEvent
        if mtype == QEvent.MouseButtonPress:
            super().mousePressEvent(fake)
        elif mtype == QEvent.MouseMove:
            super().mouseMoveEvent(fake)
        elif mtype == QEvent.MouseButtonRelease:
            super().mouseReleaseEvent(fake)
            
        event.accept()

    def event(self, event):
        # catch raw tablet events early and handle them (prevents Qt creating mouse events)
        t = event.type()
        if t in (QEvent.TabletPress, QEvent.TabletMove, QEvent.TabletRelease):
            self.tabletEvent(event)
            return True
        return super().event(event)

    # PANNING
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
        self._pen_active = False
        if event.button() == Qt.RightButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # ZOOMING
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            zoomInFactor = 1.15
            zoomOutFactor = 1 / zoomInFactor
            current_scale = self.transform().m11()
            factor = zoomInFactor if event.angleDelta().y() > 0 else zoomOutFactor
            new_scale = current_scale * factor

            if new_scale < self._min_scale:
                factor = self._min_scale / current_scale
            elif new_scale > self._max_scale:
                factor = self._max_scale / current_scale

            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

        # Drag & Drop support (Datei ins View ziehen)
    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasImage():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        scene = self.scene()
        if not scene:
            event.ignore()
            return

        # drop position in scene coords
        pos = self.mapToScene(event.position().toPoint() if hasattr(event, "position") else event.pos())

        # Dateien
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    scene.paste_file(url.toLocalFile(), view=self, at_scene_pos=pos)
                    # for simplicity only first file -> break
                    break
            event.acceptProposedAction()
            return

        # Image data
        if mime.hasImage():
            # fallback to scene.paste_from_clipboard
            scene.paste_from_clipboard(view=self, at_scene_pos=pos)
            event.acceptProposedAction()
            return

        event.ignore()



# ----------------- SafeShapeMixin -----------------
from PySide6.QtGui import QPainterPath


class SafeShapeMixin:
    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path
