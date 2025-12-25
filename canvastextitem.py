from PySide6.QtWidgets import (
    QGraphicsTextItem, QGraphicsItem, QStyleOptionGraphicsItem, QWidget,
    QMenu, QDialog, QVBoxLayout, QDateTimeEdit, QPushButton
)
from PySide6.QtGui import QPen, QColor, QBrush, QFont, QTextCursor, QUndoCommand, QPainterPath
from PySide6.QtCore import QRectF, Qt, QPointF, QDateTime, QTimer
import datetime
import notify
import uuid



class CanvasTextItem(QGraphicsTextItem):
    def __init__(self, text="", parent=None, start_edit=True):
        super().__init__(text, parent)
        self.note_id = uuid.uuid4().hex


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

        # deadline state
        self.deadline: datetime.datetime | None = None
        self._deadline_set_at: datetime.datetime | None = None
        self._deadline_pre_notified: bool = False
        self._deadline_notified: bool = False
        self._deadline_task_name = None  # optional: name of scheduled system task

    # ----------------- Hintergrund -----------------
    def boundingRect(self) -> QRectF:
        rect = super().boundingRect()
        return rect.adjusted(-self._padding, -self._padding, self._padding, self._padding)

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
            # mark scene dirty
            try:
                self.scene().mark_dirty()
            except Exception:
                pass

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

    # ----------------- Kontextmenü für Deadline -----------------
    def contextMenuEvent(self, event):
        menu = QMenu()
        set_deadline_action = menu.addAction("Deadline setzen...")
        clear_deadline_action = menu.addAction("Deadline löschen")
        action = menu.exec_(event.screenPos())

        if action == set_deadline_action:
            self._open_deadline_dialog()
        elif action == clear_deadline_action:
            # remove scheduled system task if exists
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
            # Qt -> Python datetime
            py_dt = qdt.toPython() if hasattr(qdt, "toPython") else datetime.datetime(
                qdt.date().year(), qdt.date().month(), qdt.date().day(),
                qdt.time().hour(), qdt.time().minute(), qdt.time().second()
            )
            self.set_deadline(py_dt)

    # ----------------- Deadline-Logik -----------------
    def set_deadline(self, dt: datetime.datetime):
        """Set or change deadline (local naive datetime)."""
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
        # delete scheduled task if any
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
        """Berechnet Vorwarnzeit P = clamp((deadline - set_at)/6, 5min, 1day)."""
        if not self.deadline or not self._deadline_set_at:
            return datetime.timedelta(minutes=5)
        total = self.deadline - self._deadline_set_at
        if total.total_seconds() <= 0:
            return datetime.timedelta(minutes=5)
        pre = total / 6  # timedelta division -> timedelta
        min_t = datetime.timedelta(minutes=5)
        max_t = datetime.timedelta(days=1)
        if pre < min_t:
            return min_t
        if pre > max_t:
            return max_t
        return pre

    # ----------------- Painting + Swiss date format -----------------
    def paint(self, painter, option: QStyleOptionGraphicsItem, widget: QWidget | None):
        # Background + border
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(QPen(self._border_color, 2))
        painter.drawRoundedRect(self.boundingRect(), 6, 6)

        # Draw the regular text / editor contents
        super().paint(painter, option, widget)

        # Overlay: Deadline (Swiss date format)
        if self.deadline:
            now = datetime.datetime.now()
            remaining = self.deadline - now
            pre = self._compute_pre_notify_delta()

            # choose color: red if overdue, yellow if within pre-window, default small highlight otherwise
            if remaining.total_seconds() <= 0:
                pen_color = QColor("#ff5555")  # red = overdue
            elif remaining <= pre:
                pen_color = QColor("#ffdd55")  # yellow = pre-warning
            else:
                pen_color = QColor("#bbbbbb")  # subtle gray for distant deadlines

            # Label: swiss format dd.MM.YYYY HH:MM
            try:
                label_date = self.deadline.strftime("%d.%m.%Y %H:%M")
            except Exception:
                label_date = str(self.deadline)

            if remaining.total_seconds() > 0:
                remaining_str = str(remaining).split(".")[0]
                label = f"⏳ {label_date} ({remaining_str})"
            else:
                label = f"🔔 Deadline: {label_date} (abgelaufen)"

            r = self.boundingRect()
            painter.save()
            painter.setPen(pen_color)
            font = painter.font()
            font.setPointSize(max(8, font.pointSize() - 2))
            painter.setFont(font)
            x = r.right() - 4 - painter.fontMetrics().horizontalAdvance(label)
            y = r.bottom() - 4
            painter.drawText(x, y, label)
            painter.restore()
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
