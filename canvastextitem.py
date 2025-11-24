from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtGui import QPen, QColor, QBrush, QFont
from PySide6.QtCore import QRectF, Qt, QPointF


class CanvasTextItem(QGraphicsTextItem):
    def __init__(self, text="", parent=None, start_edit=True):
        super().__init__(text, parent)

        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemSendsGeometryChanges
        )

        # Style
        self._padding = 10
        self._bg_color = QColor(30, 30, 30)
        self._border_color = QColor(120, 120, 120)
        self.setFont(QFont("Arial", 16))
        self.setDefaultTextColor(QColor("#eeeeee"))

        # Editiermodus
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        if start_edit:
            self.activate_edit_mode()  # ← Cursor ans Ende, nichts markiert

            
    # ----------------- Hintergrund -----------------
    def boundingRect(self) -> QRectF:
        rect = super().boundingRect()
        return rect.adjusted(-self._padding, -self._padding,
                             self._padding, self._padding)

    def paint(self, painter, option: QStyleOptionGraphicsItem, widget: QWidget | None):
        # Hintergrund
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(QPen(self._border_color, 2))
        painter.drawRoundedRect(self.boundingRect(), 6, 6)

        # Text
        super().paint(painter, option, widget)

    # ----------------- Doppelklick: editieren -----------------
    def mouseDoubleClickEvent(self, event):
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        super().mouseDoubleClickEvent(event)

    # ----------------- Fokusverlust -----------------
    def focusOutEvent(self, event):
        # Wenn leer → entfernen
        if self.toPlainText().strip() == "":
            if self.scene():
                self.scene().removeItem(self)
            return

        # Sonst Editiermodus ausschalten
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        super().focusOutEvent(event)

    def activate_edit_mode(self):
        from PySide6.QtGui import QTextCursor

        # Editiermodus aktivieren
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)

        # Cursor ans Ende, Auswahl löschen
        cursor = self.textCursor()
        cursor.setPosition(len(self.toPlainText()))
        cursor.clearSelection()
        self.setTextCursor(cursor)