from PySide6.QtGui import QUndoCommand, QPixmap


class PixmapCommand(QUndoCommand):
    def __init__(self, pixmap_item, before_pixmap: QPixmap, after_pixmap: QPixmap):
        super().__init__("Draw Stroke")

        # Referenz zum QGraphicsPixmapItem
        self.pixmap_item = pixmap_item

        # Kopien der Pixelbilder (sehr wichtig!)
        self.before = before_pixmap.copy()
        self.after = after_pixmap.copy()

    def undo(self):
        self.pixmap_item.setPixmap(self.before)

    def redo(self):
        self.pixmap_item.setPixmap(self.after)