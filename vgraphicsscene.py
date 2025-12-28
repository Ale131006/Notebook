
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QApplication
from PySide6.QtGui import (
    QPixmap, QPainter, QPainterPath, QPen, QTransform,
    QColor, QUndoCommand, QImage
)
from PySide6.QtCore import Qt, QRectF, QPointF
from canvastextitem import CanvasTextItem
import os

import uuid, os
from pathlib import Path
from PySide6.QtGui import QImage, QPainter
from uuid import uuid4

# ----------------- Safe Pixmap Item -----------------
class SafePixmapItem(QGraphicsPixmapItem):
    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path
    




# ----------------- GraphicsFileItem (movable image/file) -----------------
class GraphicsFileItem(QGraphicsPixmapItem):
    def __init__(
        self,
        pixmap,
        file_path: str | None = None,
        asset_id: str | None = None,
        original_path: str | None = None 
    ):
        super().__init__(pixmap)
        from PySide6.QtWidgets import QGraphicsItem
        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsMovable
        )
        self.file_path = file_path
        self.original_path = original_path
        self.asset_id = asset_id or uuid.uuid4().hex

    # ----------------- Clipboard / Paste support -----------------
    def _cap_pixmap(pix: 'QPixmap', max_dim=1200):
        """Skaliere große Bilder runter (vermeidet speicher- und rendering-probleme)."""
        w = pix.width()
        h = pix.height()
        if max(w, h) <= max_dim:
            return pix
        if w >= h:
            new_w = max_dim
            new_h = int(h * (max_dim / w))
        else:
            new_h = max_dim
            new_w = int(w * (max_dim / h))
        return pix.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    def mouseDoubleClickEvent(self, event):
        path = self.original_path or self.file_path
        if isinstance(path, str) and path.lower().endswith(".pdf"):
            import os, subprocess, sys
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

        super().mouseDoubleClickEvent(event)







# ----------------- View Graphics Scene -----------------
class ViewGraphicsScene(QGraphicsScene):
    def __init__(self, main_window, width=5000, height=5000, grid_size=100):
        super().__init__()
        self.main_window = main_window
        self.last_pos = None
        self._move_counter = 0
        #self.undo_stack = main_window.undo_stack          #UNDO (Auskommentiert wegen Fehler)
        self.setSceneRect(0, 0, width, height)
        # Drawing state
        self.drawing = False
        enabled = False
        self.eraser_enabled = False
        self.pen_color = QColor("white")
        self.pen_width = 3
        # Pixmap
        self._pre_pixmap = None
        self.canvas_pixmap = QPixmap(width, height)
        self.canvas_pixmap.fill(Qt.transparent)
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

     # ----------------- Clipboard / File paste helpers -----------------
    def _cap_pixmap(self, pix: QPixmap, max_dim=1200) -> QPixmap:
        """Skaliere große Bilder runter (vermeidet Speicher-/Rendering-Probleme)."""
        w = pix.width()
        h = pix.height()
        if max(w, h) <= max_dim:
            return pix
        if w >= h:
            new_w = max_dim
            new_h = int(h * (max_dim / w))
        else:
            new_h = max_dim
            new_w = int(w * (max_dim / h))
        return pix.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def paste_from_clipboard(self, view=None, at_scene_pos: 'QPointF | None' = None):
        """
        Fügt aus der Zwischenablage ein:
          - Bild (wenn verfügbar)
          - lokale Datei-URL (erste lokale Datei)
        Wenn view gegeben, positioniert an der View-Mitte (oder an at_scene_pos).
        Rückgabe: das eingefügte GraphicsFileItem oder None.
        """

        cb = QApplication.clipboard()
        mime = cb.mimeData()

        # 1) Image direkt aus clipboard
        if mime.hasImage():
            img = cb.image()
            if isinstance(img, QImage):
                pix = QPixmap.fromImage(img)
            else:
                pix = QPixmap()
                pix.loadFromData(img)

            pix = self._cap_pixmap(pix)

            from uuid import uuid4
            from pathlib import Path

            mw = self.main_window
            idx = mw.list_notebooks.currentRow()
            if idx < 0:
                return None

            nb_path = Path(mw.notebooks[idx]["path"])
            img_dir = nb_path / "assets" / "images"
            img_dir.mkdir(parents=True, exist_ok=True)

            img_name = f"{uuid4().hex}.png"
            img_path = img_dir / img_name
            ok = pix.save(str(img_path), "PNG")

            if not ok:
                print("ERROR: pixmap could not be saved!")
                return None

            return self._insert_pixmap(
                QPixmap(str(img_path)),
                view,
                at_scene_pos,
                file_path=str(img_path)
            )

        # 2) URLs (Dateien) — nehme erste lokale Datei
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    return self.paste_file(path, view, at_scene_pos)

        return None

    def paste_file(self, path: str, view=None, at_scene_pos: 'QPointF | None' = None):
        """
        Fügt eine lokale Datei ein. Unterstützt Bilder direkt.
        PDFs werden als Vorschau (erste Seite) gerendert, Originalpfad bleibt erhalten.
        """
        if not os.path.exists(path):
            return None

        lower = path.lower()

        # 1) Bilder direkt einfügen
        if lower.endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff")):
            pix = QPixmap(path)
            if pix.isNull():
                return None
            pix = self._cap_pixmap(pix)
            return self._insert_pixmap(pix, view, at_scene_pos, file_path=path)

        # 2) PDFs rendern (erste Seite)
        if lower.endswith(".pdf"):
            try:
                from PySide6.QtPdf import QPdfDocument, QPdfDocumentRenderOptions
                from PySide6.QtCore import QSize
                from PySide6.QtGui import QImage
            except Exception:
                print("QtPdf nicht verfügbar")
                return None

            doc = QPdfDocument(self)
            status = doc.load(path)

            # Falls kein Seiteninhalt -> abbrechen
            if doc.pageCount() == 0:
                doc.deleteLater()
                print("PDF hat keine Seiten oder konnte nicht geladen werden.")
                return None

            page = 0
            try:
                page_size = doc.pagePointSize(page)  # QSizeF oder QSize-like
                pw = int(page_size.width())
                ph = int(page_size.height())
            except Exception:
                pw, ph = 800, 1100

            # skaliere etwas höher auflösung zum Schärfen
            scale = 2.0
            target_w = max(1, int(pw * scale))
            target_h = max(1, int(ph * scale))

            opts = QPdfDocumentRenderOptions()

            image = None
            try:
                image = doc.render(page, QSize(target_w, target_h), opts)
                if isinstance(image, QImage):
                    fixed = QImage(image.size(), QImage.Format_ARGB32)
                    fixed.fill(Qt.white)
                    painter = QPainter(fixed)
                    painter.drawImage(0, 0, image)
                    painter.end()
                    image = fixed
                print("PDF image format:", image.format())
            
                if not isinstance(image, QImage):
                
                    image = None
            except TypeError:
            
                image = None
            except Exception as e:
                print("PDF render (QSize) Fehlgeschlagen:", e)
                image = None

            # 2) Fallback: ältere Signatur render(page, QImage, opts) -> bool
            if image is None:
                try:
                    img = QImage(target_w, target_h, QImage.Format_ARGB32)
                    img.fill(Qt.white)
                    ok = doc.render(page, img, opts)
                    if ok:
                        image = img
                    else:
                        image = None
                except Exception as e:
                    print("PDF render (QImage) Fallback fehlgeschlagen:", e)
                    image = None

            if image is None:
                doc.deleteLater()
                print("PDF-Seite konnte nicht gerendert werden.")
                return None

            # Pixmap erzeugen
            pix = QPixmap.fromImage(image)
            pix = GraphicsFileItem._cap_pixmap(pix, max_dim=1600)


            mw = self.main_window
            idx = mw.list_notebooks.currentRow()
            nb_path = Path(mw.notebooks[idx]["path"])
            img_dir = nb_path / "assets" / "images"
            img_dir.mkdir(parents=True, exist_ok=True)

            img_name = f"{uuid4().hex}.png"
            img_path = img_dir / img_name
            pix.save(str(img_path), "PNG")

            doc.deleteLater()

            return self._insert_pixmap(
                pix,
                view,
                at_scene_pos,
                file_path=str(img_path),
                original_path=path
            )
        # 3) Andere Dateien → Platzhalter
        txt = os.path.basename(path)
        w, h = 300, 100
        placeholder = QPixmap(w, h)
        placeholder.fill(QColor(240, 240, 240))

        painter = QPainter(placeholder)
        painter.setPen(QColor(40, 40, 40))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(placeholder.rect(), Qt.AlignCenter, txt)
        painter.end()

        pix = self._cap_pixmap(placeholder, max_dim=800)
        return self._insert_pixmap(pix, view, at_scene_pos, file_path=path)

    def _insert_pixmap(
            self,
            pix: QPixmap,
            view=None,
            at_scene_pos=None,
            file_path=None,
            original_path=None
        ):
        item = GraphicsFileItem(
            pix,
            file_path=file_path,
            original_path=original_path,
            asset_id=Path(file_path).stem if file_path else None
        )

        item.setZValue(-100)
        self.addItem(item)

        if at_scene_pos is not None:
            item.setPos(at_scene_pos)
        else:
            if view is None:
                views = self.views()
                view = views[0] if views else None
            if view is not None:
                center = view.mapToScene(view.viewport().rect().center())
                item.setPos(center.x() - pix.width() / 2, center.y() - pix.height() / 2)
            else:
                item.setPos(0, 0)
        return item


    def addTextItem(self, pos):
        item = CanvasTextItem("", start_edit=True)
        item.setPos(pos)
        self.addItem(item)
        item.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        return item
    
    def mouseDoubleClickEvent(self, event):
        clicked_item = self.itemAt(event.scenePos(), QTransform())
        if clicked_item is None:
            mw = getattr(self, "main_window", None)
            fam = getattr(mw, "default_font_family", "Arial")
            fsize = getattr(mw, "default_font_size", 16)
            color = getattr(mw, "default_text_color", None)
            item = CanvasTextItem("", start_edit=True, font_family=fam, font_size=fsize, text_color=color)
            item.setPos(event.scenePos())
            self.addItem(item)
        elif isinstance(clicked_item, CanvasTextItem):
            clicked_item.activate_edit_mode()
            clicked_item.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        super().mouseDoubleClickEvent(event)
    # ----------------- Drawing Mode -----------------
    def set_drawing_mode(self, enabled: bool):
        self.drawing_enabled = enabled
    # ----------------- Mouse Events -----------------


    def mousePressEvent(self, event):

        for item in list(self.items()):
            if isinstance(item, CanvasTextItem):
                if item.toPlainText().strip() == "":
                    # nur löschen, wenn es NICHT gerade fokussiert wird
                    if item is not self.focusItem():
                        self.removeItem(item)

        if self.drawing_enabled and event.button() == Qt.LeftButton:
            self.last_pos = event.scenePos()
            self._move_counter = 0
            self._pre_pixmap = self.canvas_pixmap.copy()
            return

        clicked_items = self.items(event.scenePos())

        clicked_text = any(
            isinstance(it, CanvasTextItem) for it in clicked_items
        )

        if not clicked_text:
            for it in self.items():
                if isinstance(it, CanvasTextItem):
                    it.setTextInteractionFlags(Qt.NoTextInteraction)
                    it.clearFocus()

        super().mousePressEvent(event)



    def mouseMoveEvent(self, event):
        if self.drawing_enabled and self.last_pos is not None:
            pos = event.scenePos()
            self._move_counter += 1

            is_pen = self._is_pen_input()

            if is_pen:
            
                if self._move_counter % 15 != 0:
                    return

            
                if (pos - self.last_pos).manhattanLength() < 15:
                    return
                
            else: 
                if (pos - self.last_pos).manhattanLength() < 1.5:
                    return

            self._draw_line(self.last_pos, pos)
            self.last_pos = pos
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drawing_enabled and event.button() == Qt.LeftButton:
            post = self.canvas_pixmap.copy()
            """if self._pre_pixmap is not None:
                self.undo_stack.push(
                    PixmapCommand(self.canvas_item, self._pre_pixmap, post)  #UNDO (Auskommentiert wegen Fehler)
                )"""
            self.last_pos = None
            self._pre_pixmap = None
            self._move_counter = 0
            return

        super().mouseReleaseEvent(event)

    # ----------------- Tablet Events -----------------
    def tabletEvent(self, event):
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
        pen.setCapStyle(Qt.FlatCap)
        pen.setJoinStyle(Qt.MiterJoin)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        rect = QRectF(p1, p2).normalized()
        pad = max(4, int(self.pen_width * 1.5))
        rect = rect.adjusted(-pad, -pad, pad, pad)
        self.canvas_item.update(rect.toRect())
        self.canvas_item.setPixmap(self.canvas_pixmap)
    # ----------------- Setters -----------------
    def set_pen_color(self, color):
        self.pen_color = color
    def set_pen_width(self, width):
        self.pen_width = width
    def set_eraser_mode(self, enabled):
        self.eraser_enabled = enabled

    def keyPressEvent(self, event):
        # Prüfen, ob aktuell ein TextItem den Fokus hat
        focus_item = self.focusItem()
        if isinstance(focus_item, CanvasTextItem):
            # Key-Events an TextItem weitergeben
            super().keyPressEvent(event)
            return

        # Keine TextItems aktiv → lösche normale Items
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for item in self.selectedItems():
                if not isinstance(item, CanvasTextItem):
                    if hasattr(item, "file_path") and item.file_path:
                        try:
                            os.remove(item.file_path)
                        except Exception:
                            pass
                    self.removeItem(item)
        else:
            super().keyPressEvent(event)


    def _is_pen_input(self):
        views = self.views()
        if not views:
            return False
        view = views[0]
        return getattr(view, "_pen_active", False)
    
    def addTextItem(self, pos):
        # Verwende Default-Font-Einstellungen vom MainWindow (falls vorhanden)
        mw = getattr(self, "main_window", None)
        fam = getattr(mw, "default_font_family", "Arial")
        fsize = getattr(mw, "default_font_size", 16)
        color = getattr(mw, "default_text_color", None)
        item = CanvasTextItem("", start_edit=True, font_family=fam, font_size=fsize, text_color=color)
        item.setPos(pos)
        self.addItem(item)
        item.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        return item



"""# ----------------- PixmapCommand (Undo/Redo) -----------------
class PixmapCommand(QUndoCommand):
    def __init__(self, pixmap_item, before_pixmap, after_pixmap):
        super().__init__()
        self.pixmap_item = pixmap_item
        self.before = before_pixmap.copy()
        self.after = after_pixmap.copy()                         #UNDO (Auskommentiert wegen Fehler)
    def undo(self):
        self.pixmap_item.setPixmap(self.before)
    def redo(self):
        self.pixmap_item.setPixmap(self.after)"""
