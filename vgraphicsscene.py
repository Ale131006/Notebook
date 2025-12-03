
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem
from PySide6.QtGui import (
    QWheelEvent, QBrush, QPixmap, QPainter, QPainterPath, QPen, QTransform,
    QColor, QTextCursor, QUndoCommand, QTabletEvent
)
from PySide6.QtCore import Qt, QRectF, QSize, QTimer, QEvent
from canvastextitem import CanvasTextItem
from drawCommand import DrawCommand

# ----------------- Safe Pixmap Item -----------------
class SafePixmapItem(QGraphicsPixmapItem):
    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

# ----------------- View Graphics Scene -----------------
class ViewGraphicsScene(QGraphicsScene):
    def __init__(self, main_window, width=5000, height=5000, grid_size=100):
        super().__init__()
        self.main_window = main_window
        self.last_pos = None
        self.undo_stack = main_window.undo_stack
        # Drawing state
        self.drawing_enabled = False
        self.eraser_enabled = False
        self.pen_color = QColor("white")
        self.pen_width = 3
        # Pixmap
        self._pre_pixmap = None
        self.canvas_pixmap = QPixmap(width, height)
        self.canvas_pixmap.fill(Qt.transparent)
        """"
        self.canvas_item = SafePixmapItem(self.canvas_pixmap)
        self.addItem(self.canvas_item)
        self.canvas_item.setZValue(1)"""
        self.canvas_item = self.addPixmap(self.canvas_pixmap)
        self.canvas_item.setZValue(1)
        # Grid
        self._grid_pixmap = None
        self._grid_size = grid_size
        self._background_color = QColor(30, 30, 30)
        self._grid_color = QColor(80, 80, 80, 40)
        self._major_grid_color = QColor(120, 120, 120, 60)
        self._tile_size = self._grid_size * 8
        self._create_grid_tile()



    # ----------------- Grid -----------------
    def _create_grid_tile(self):
        size = self._tile_size
        pix = QPixmap(size, size)
        pix.fill(self._background_color)
        painter = QPainter(pix)
        pen = painter.pen()
        # Minor grid lines
        pen.setColor(self._grid_color)
        painter.setPen(pen)
        for x in range(0, size, self._grid_size):
            painter.drawLine(x, 0, x, size)
        for y in range(0, size, self._grid_size):
            painter.drawLine(0, y, size, y)
        # Major grid lines
        pen.setColor(self._major_grid_color)
        pen.setWidth(2)
        painter.setPen(pen)
        major = self._grid_size * 8
        for x in range(0, size, major):
            painter.drawLine(x, 0, x, size)
        for y in range(0, size, major):
            painter.drawLine(0, y, size, y)
        painter.end()
        self._grid_pixmap = pix
    def drawBackground(self, painter, rect: QRectF):
        if not self._grid_pixmap:
            return
        tile = self._grid_pixmap
        ts = tile.size()
        left = int(rect.left()) - (int(rect.left()) % ts.width())
        top = int(rect.top()) - (int(rect.top()) % ts.height())
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPixmap(x, y, tile)
                y += ts.height()
            x += ts.width()
    # ----------------- Text Item -----------------
    def addTextItem(self, pos):
        item = CanvasTextItem("", start_edit=True)
        item.setPos(pos)
        self.addItem(item)
        return item
    def mouseDoubleClickEvent(self, event):
        print("Scene Double Click at", event.scenePos())
        clicked_item = self.itemAt(event.scenePos(), QTransform())
        print("Clicked item:", clicked_item)
        if clicked_item is None:
            print("Adding new text item")
            item = CanvasTextItem("", start_edit=True)
            item.setPos(event.scenePos())
            self.addItem(item)
        elif isinstance(clicked_item, CanvasTextItem):
            print("Activating edit mode for clicked text item")
            clicked_item.activate_edit_mode()
        super().mouseDoubleClickEvent(event)
        print("fertig")
    # ----------------- Drawing Mode -----------------
    def set_drawing_mode(self, enabled: bool):
        self.drawing_enabled = enabled
    # ----------------- Mouse Events -----------------
    def mousePressEvent(self, event):
        if self.drawing_enabled and event.button() == Qt.LeftButton:
            self._pre_pixmap = self.canvas_pixmap.copy()
            self.last_pos = event.scenePos()
            return
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self.drawing_enabled and self.last_pos is not None:
            self._draw_line(self.last_pos, event.scenePos())
            self.last_pos = event.scenePos()
            return
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if self.drawing_enabled and event.button() == Qt.LeftButton:
            self.last_pos = None
            post = self.canvas_pixmap.copy()
            if self._pre_pixmap is not None:
                self.undo_stack.push(PixmapCommand(self.canvas_item, self._pre_pixmap, post))
            self._pre_pixmap = None
            return
        super().mouseReleaseEvent(event)
    # ----------------- Tablet Events -----------------
    def tabletEvent(self, event):
        # Niemals Tablet-Events hier behandeln!
        # Sie wurden im View bereits in MouseEvents umgewandelt.
        # Scene darf sie weder ignorieren noch akzeptieren.
        return
    # ----------------- Draw Routine -----------------
    def _draw_line(self, p1, p2):
        painter = QPainter(self.canvas_pixmap)
        if self.eraser_enabled:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            pen = QPen(Qt.transparent, self.pen_width)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(self.pen_color, self.pen_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        # Update changed region
        rect = QRectF(p1, p2).normalized()
        pad = max(4, int(self.pen_width * 1.5))
        rect = rect.adjusted(-pad, -pad, pad, pad)
        self.canvas_item.setPixmap(self.canvas_pixmap)
        self.canvas_item.update(rect.toRect())
    # ----------------- Setters -----------------
    def set_pen_color(self, color):
        self.pen_color = color
    def set_pen_width(self, width):
        self.pen_width = width
    def set_eraser_mode(self, enabled):
        self.eraser_enabled = enabled

# ----------------- PixmapCommand (Undo/Redo) -----------------
class PixmapCommand(QUndoCommand):
    def __init__(self, pixmap_item, before_pixmap, after_pixmap):
        super().__init__()
        self.pixmap_item = pixmap_item
        self.before = before_pixmap.copy()
        self.after = after_pixmap.copy()
    def undo(self):
        self.pixmap_item.setPixmap(self.before)
    def redo(self):
        self.pixmap_item.setPixmap(self.after)
