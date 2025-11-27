from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtGui import QPen, QColor, QBrush, QFont, QTextCursor, QUndoCommand, QPainterPath
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

        # Für Undo/Redo
        self._old_text = text
        self._new_text = text
        self._old_pos = self.pos()
        self._new_pos = self.pos()

        # Editiermodus
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        if start_edit:
            self.activate_edit_mode()

    # ----------------- Hintergrund -----------------
    def boundingRect(self) -> QRectF:
        rect = super().boundingRect()
        return rect.adjusted(-self._padding, -self._padding, self._padding, self._padding)

    def paint(self, painter, option: QStyleOptionGraphicsItem, widget: QWidget | None):
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(QPen(self._border_color, 2))
        painter.drawRoundedRect(self.boundingRect(), 6, 6)
        super().paint(painter, option, widget)

    # ----------------- Editieren per Doppelklick -----------------
    def mouseDoubleClickEvent(self, event):
        self._old_text = self.toPlainText()  # Text vor Änderung merken
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        super().mouseDoubleClickEvent(event)

    # ----------------- Fokusverlust: Edit-Ende -----------------
    def focusOutEvent(self, event):
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self._new_text = self.toPlainText()

        # Wenn leer → Löschbefehl
        if self._new_text.strip() == "":
            cmd = DeleteTextCommand(self.scene(), self)
            self.scene().undo_stack.push(cmd)
            return

        # Text wirklich geändert?
        if self._old_text != self._new_text:
            cmd = TextEditCommand(self, self._old_text, self._new_text)
            self.scene().undo_stack.push(cmd)

        super().focusOutEvent(event)

    # ----------------- Verschieben Undo/Redo -----------------
    def itemChange(self, change, value):
        # Beim Start der Bewegung → alte Position speichern
        if change == QGraphicsItem.ItemPositionChange:
            self._old_pos = self.pos()
            self._new_pos = value

        # Bewegung abgeschlossen → MoveCommand pushen
        if change == QGraphicsItem.ItemPositionHasChanged:
            if self.scene() and self._old_pos != self._new_pos:
                cmd = MoveCommand(self, self._old_pos, self._new_pos)
                self.scene().undo_stack.push(cmd)

        return super().itemChange(change, value)

    # ----------------- Editiermodus per Code aktivieren -----------------
    def activate_edit_mode(self):
        self._old_text = self.toPlainText()
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        cursor = self.textCursor()
        cursor.setPosition(len(self.toPlainText()))
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def shape(self):
        path = QPainterPath()
        rect = self.boundingRect()
        path.addRoundedRect(rect, 6, 6)
        return path


# ============================================================
# Undo/Redo Commands
# ============================================================
class TextEditCommand(QUndoCommand):
    def __init__(self, item, old, new):
        super().__init__("Edit Text")
        self.item = item
        self.old = old
        self.new = new

    def undo(self):
        self.item.setPlainText(self.old)

    def redo(self):
        self.item.setPlainText(self.new)


class MoveCommand(QUndoCommand):
    def __init__(self, item, old_pos, new_pos):
        super().__init__("Move Item")
        self.item = item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def undo(self):
        self.item.setPos(self.old_pos)

    def redo(self):
        self.item.setPos(self.new_pos)


class DeleteTextCommand(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__("Delete Text")
        self.scene = scene
        self.item = item
        self.pos = item.pos()
        self.text = item.toPlainText()

    def undo(self):
        self.scene.addItem(self.item)
        self.item.setPos(self.pos)
        self.item.setPlainText(self.text)

    def redo(self):
        self.scene.removeItem(self.item)
