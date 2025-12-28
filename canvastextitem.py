from PySide6.QtWidgets import (
    QGraphicsTextItem, QGraphicsItem, QStyleOptionGraphicsItem,
    QMenu, QDialog, QVBoxLayout, QDateTimeEdit, QPushButton
)
from PySide6.QtGui import QPen, QColor, QBrush, QFont, QUndoCommand, QPainterPath
from PySide6.QtCore import QRectF, Qt, QDateTime
import datetime
import notify




class CanvasTextItem(QGraphicsTextItem):
    def __init__(self, text="", parent=None, start_edit=True,
                 font_family: str = "Arial", font_size: int = 16, text_color = None):
        super().__init__(text, parent)

        # Flags
        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsFocusable |
            QGraphicsItem.ItemSendsGeometryChanges
        )

        # Style defaults
        self._padding = 25
        self._bg_color = QColor(30, 30, 30)
        self._border_color = QColor(120, 120, 120)
        self._focused_border_color = QColor("#ffd24d")
        self._focused_border_width = 3

        # Font / Color
        self.font_family = font_family or "Arial"
        self.font_size = int(font_size or 16)
        f = QFont(self.font_family, self.font_size)
        self.setFont(f)
        if text_color is None:
            text_color = QColor("#eeeeee")
        elif isinstance(text_color, str):
            text_color = QColor(text_color)
        self.text_color = text_color.name()
        self.setDefaultTextColor(QColor(self.text_color))

        # Für Undo/Redo
        self._old_text = text
        self._new_text = text
        self._old_pos = self.pos()
        self._new_pos = self.pos()

        # Editiermodus
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        if start_edit:
            self.activate_edit_mode()

        # deadline state
        self.deadline: datetime.datetime | None = None
        self._deadline_set_at: datetime.datetime | None = None
        self._deadline_pre_notified: bool = False
        self._deadline_notified: bool = False
        self._deadline_task_name = None

    def boundingRect(self) -> QRectF:
        rect = super().boundingRect()
        return rect.adjusted(-self._padding, -self._padding, self._padding, self._padding)

    

    def mouseDoubleClickEvent(self, event):
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        self.activate_edit_mode()

        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

        event.accept()

    def mousePressEvent(self, event):

        if self.textInteractionFlags() == Qt.NoTextInteraction and \
            self.toPlainText().strip() == "":
                scene = self.scene()
                if scene:
                    scene.removeItem(self)
                    event.accept()
                    return


        if self.textInteractionFlags() == Qt.TextEditorInteraction:
            self.setFocus(Qt.MouseFocusReason)
            super().mousePressEvent(event)
            return

        super().mousePressEvent(event)


    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self._old_pos = self.pos()
            self._new_pos = value
        if change == QGraphicsItem.ItemPositionHasChanged:
            if self.scene() and self._old_pos != self._new_pos:
                cmd = MoveCommand(self, self._old_pos, self._new_pos)
                #self.scene().undo_stack.push(cmd)              #UNDO (Auskommentiert wegen Fehler)
        return super().itemChange(change, value)

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

    def contextMenuEvent(self, event):
        menu = QMenu()
        set_deadline_action = menu.addAction("Deadline setzen...")
        clear_deadline_action = menu.addAction("Deadline löschen")
        action = menu.exec_(event.screenPos())
        if action == set_deadline_action:
            self._open_deadline_dialog()
        elif action == clear_deadline_action:
            if self._deadline_task_name:
                try:
                    notify.delete_scheduled_task(self._deadline_task_name)
                except Exception:
                    pass
                self._deadline_task_name = None
            self.clear_deadline()

    def _open_deadline_dialog(self):
        dlg = QDialog()
        dlg.setWindowTitle("Deadline setzen")
        layout = QVBoxLayout(dlg)
        dt_edit = QDateTimeEdit(dlg)
        dt_edit.setCalendarPopup(True)
        dt_edit.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(dt_edit)
        btn_ok = QPushButton("OK", dlg)
        btn_cancel = QPushButton("Abbrechen", dlg)
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        layout.addWidget(btn_ok)
        layout.addWidget(btn_cancel)
        if dlg.exec() == QDialog.Accepted:
            qdt = dt_edit.dateTime()
            py_dt = qdt.toPython() if hasattr(qdt, "toPython") else datetime.datetime(
                qdt.date().year(), qdt.date().month(), qdt.date().day(),
                qdt.time().hour(), qdt.time().minute(), qdt.time().second()
            )
            self.set_deadline(py_dt)

    def set_deadline(self, dt: datetime.datetime):
        self.deadline = dt
        self._deadline_set_at = datetime.datetime.now()
        self._deadline_pre_notified = False
        self._deadline_notified = False
        self.update()
        try:
            self.scene().mark_dirty()
        except Exception:
            pass

    def clear_deadline(self):
        self.deadline = None
        self._deadline_set_at = None
        self._deadline_pre_notified = False
        self._deadline_notified = False
        if self._deadline_task_name:
            try:
                notify.delete_scheduled_task(self._deadline_task_name)
            except Exception:
                pass
            self._deadline_task_name = None
        self.update()
        try:
            self.scene().mark_dirty()
        except Exception:
            pass

    def _compute_pre_notify_delta(self) -> datetime.timedelta:
        if not self.deadline or not self._deadline_set_at:
            return datetime.timedelta(minutes=5)
        total = self.deadline - self._deadline_set_at
        if total.total_seconds() <= 0:
            return datetime.timedelta(minutes=5)
        pre = total / 6
        min_t = datetime.timedelta(minutes=5)
        max_t = datetime.timedelta(days=1)
        if pre < min_t:
            return min_t
        if pre > max_t:
            return max_t
        return pre

    def focusOutEvent(self, event):
        scene = self.scene()
        if scene and scene.views():
            view = scene.views()[0]
            if view.hasFocus():
                event.ignore()
                return
            

        if scene and self._is_effectively_empty():
            scene.removeItem(self)
            event.accept()
            return
            
        """new_text = self.toPlainText()

        if scene and new_text != self._old_text:
            cmd = TextEditCommand(self, self._old_text, new_text) #UNDO (Auskommentiert wegen Fehler)
            scene.undo_stack.push(cmd)"""

        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

        self.setTextInteractionFlags(Qt.NoTextInteraction)
        super().focusOutEvent(event)


    def exit_edit_mode(self):
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.clearFocus()


    def paint(self, painter, option: QStyleOptionGraphicsItem, widget=None):
        # Hintergrund + Rahmen
        painter.setBrush(QBrush(self._bg_color))

        if self.hasFocus() or self.isSelected():
            pen = QPen(self._focused_border_color, self._focused_border_width)
        else:
            pen = QPen(self._border_color, 2)

        painter.setPen(pen)
        painter.drawRoundedRect(self.boundingRect(), 6, 6)

        # Text zeichnen
        super().paint(painter, option, widget)

        # 🔔 Deadline Overlay
        if self.deadline:
            now = datetime.datetime.now()
            remaining = self.deadline - now
            pre = self._compute_pre_notify_delta()

            if remaining.total_seconds() <= 0:
                pen_color = QColor("#ff5555")
            elif remaining <= pre:
                pen_color = QColor("#ffdd55")
            else:
                pen_color = QColor("#bbbbbb")

            label_date = self.deadline.strftime("%d.%m.%Y %H:%M")

            if remaining.total_seconds() > 0:
                remaining_str = str(remaining).split(".")[0]
                label = f"⏳ {label_date} ({remaining_str})"
            else:
                label = f"🔔 Deadline: {label_date} (abgelaufen)"

            painter.save()
            painter.setPen(pen_color)
            font = painter.font()
            font.setPointSize(max(8, font.pointSize() - 2))
            painter.setFont(font)

            r = self.boundingRect()
            x = r.right() - 6 - painter.fontMetrics().horizontalAdvance(label)
            y = r.bottom() - 6

            painter.drawText(x, y, label)
            painter.restore()

    def _is_effectively_empty(self) -> bool:
        return self.toPlainText().strip() == ""


    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            scene = self.scene()
            if not scene:
                return

            if self.toPlainText().strip() == "" or \
            self.textInteractionFlags() == Qt.NoTextInteraction:

                cmd = DeleteTextCommand(scene, self)
                #scene.undo_stack.push(cmd)          #UNDO (Auskommentiert wegen Fehler)
                event.accept()
                return

        super().keyPressEvent(event)



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
