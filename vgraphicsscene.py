from PySide6.QtWidgets import QGraphicsScene, QGraphicsView
from PySide6.QtGui import QWheelEvent, QBrush, QPixmap, QPainter, QPainterPath, QPen, QTransform, QColor, QTextCursor
from PySide6.QtCore import Qt, QRectF, QSize 
from canvastextitem import CanvasTextItem

class ViewGraphicsScene(QGraphicsScene):
    def __init__(self, main_window,  width=5000, height=5000, grid_size=100):
        super().__init__()
        self.main_window = main_window

        self.last_pos = None

        #self.setSceneRect(0, 0, width, height)
        #self.ensureVisible(0, 0, 1, 1)

        self.drawing_enabled = False
        self.eraser_enabled = False
        self.pen_color = QColor("white")
        self.pen_width = 3
        self._current_path = None

        self.canvas_pixmap = QPixmap(width, height)
        self.canvas_pixmap.fill(Qt.transparent)

        self.canvas_item = self.addPixmap(self.canvas_pixmap)
        self.canvas_item.setZValue(1)

        self._grid_pixmap = None
        self._grid_size = grid_size
        self._background_color = QColor(30, 30, 30)   # dunkles Grau
        self._grid_color = QColor(80, 80, 80, 40)     # dezente Linien
        self._major_grid_color = QColor(120, 120, 120, 60)

        self._tile_size = self._grid_size * 8
        self._create_grid_tile()
        

    def _create_grid_tile(self):
        size = self._tile_size
        pix = QPixmap(size, size)
        pix.fill(self._background_color)
        painter = QPainter(pix)
        # Draw minor grid lines
        pen = painter.pen()
        pen.setColor(self._grid_color)
        painter.setPen(pen)
        for x in range(0, size, self._grid_size):
            painter.drawLine(x, 0, x, size)
        for y in range(0, size, self._grid_size):
            painter.drawLine(0, y, size, y)
        # Draw major grid lines (every 8th)
        pen.setColor(self._major_grid_color)
        pen.setWidth(2)
        painter.setPen(pen)
        step = self._grid_size * 8
        for x in range(0, size, step):
            painter.drawLine(x, 0, x, size)
        for y in range(0, size, step):
            painter.drawLine(0, y, size, y)
        painter.end()
        self._grid_pixmap = pix

    def drawBackground(self, painter, rect: QRectF):
        """
        Der Hintergrund wird mit einer gekachelten Pixmap dargestellt.
        Qt ruft drawBackground nur für sichtbare Bereiche auf — performant.
        """
        if not self._grid_pixmap:
            return

        tile = self._grid_pixmap
        ts = tile.size()
        # Berechne Startkoordinaten so, dass Kacheln nahtlos liegen
        left = int(rect.left()) - (int(rect.left()) % ts.width())
        top = int(rect.top()) - (int(rect.top()) % ts.height())

        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPixmap(x, y, tile)
                y += ts.height()
            x += ts.width()

    
    def addTextItem(self, pos):
        item = CanvasTextItem("", start_edit=True)
        item.setPos(pos)
        self.addItem(item)
        return item

    def mouseDoubleClickEvent(self, event):
        clicked_item = self.itemAt(event.scenePos(), QTransform())

        if clicked_item is None:
            # Neues Textfeld erstellen
            item = CanvasTextItem("", start_edit=True)
            item.setPos(event.scenePos())
            self.addItem(item)

        else:
            # Doppelklick auf bestehendes CanvasTextItem → Editieren
            if isinstance(clicked_item, CanvasTextItem):
                clicked_item.activate_edit_mode()

            super().mouseDoubleClickEvent(event)

    def set_drawing_mode(self, enabled: bool):
        self.is_drawing = enabled

    def mousePressEvent(self, event):
        if self.drawing_enabled:
            self.last_pos = event.scenePos()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing_enabled and self.last_pos is not None:

            painter = QPainter(self.canvas_pixmap)

            if self.eraser_enabled:
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                pen = QPen(Qt.transparent, self.pen_width)
            else:
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                pen = QPen(self.pen_color, self.pen_width)

            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)

            painter.drawLine(self.last_pos, event.scenePos())
            painter.end()

            self.canvas_item.setPixmap(self.canvas_pixmap)
            self.last_pos = event.scenePos()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.last_pos = None
        super().mouseReleaseEvent(event)


    def set_drawing_mode(self, enabled):
        self.drawing_enabled = enabled
        # Radierer bleibt wie er ist

    def set_pen_color(self, color):
        self.pen_color = color

    def set_pen_width(self, width):
        self.pen_width = width

    def set_eraser_mode(self, enabled):
        self.eraser_enabled = enabled