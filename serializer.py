# serializer.py
import json
import os
import shutil
import uuid
from pathlib import Path
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtCore import QPointF
from canvastextitem import CanvasTextItem
from vgraphicsscene import GraphicsFileItem
import datetime

def _ensure_assets_folder(nb_path: Path) -> Path:
    assets = nb_path / "assets" / "images"
    assets.mkdir(parents=True, exist_ok=True)
    return assets

def _copy_asset(src: str, assets_folder: Path) -> str:
    """Copy src into assets_folder and return relative filename."""
    if not os.path.exists(src):
        return None
    ext = Path(src).suffix
    dst_name = f"{uuid.uuid4().hex}{ext}"
    dst = assets_folder / dst_name
    try:
        shutil.copy2(src, str(dst))
        return str(Path("assets") / dst_name)  # store relative path
    except Exception:
        return None

def serialize_scene(scene, nb_path: str) -> str:
    nb_path = Path(nb_path)
    assets = _ensure_assets_folder(nb_path)
    items = []
    # Save canvas pixmap to file (if present)
    try:
        pixmap = scene.canvas_pixmap
        if pixmap and not pixmap.isNull():
            canvas_fn = "canvas.png"
            canvas_path = nb_path / canvas_fn
            pixmap.save(str(canvas_path), "PNG")
        else:
            canvas_fn = None
    except Exception:
        canvas_fn = None

    for item in scene.items():
        # Canvas pixmap item (skip since saved separately)
        # Text items (CanvasTextItem)

        if isinstance(item, CanvasTextItem):
            entry = {
                "type": "text",
                "html": item.toHtml(),
                "x": item.x(),
                "y": item.y(),
                "z": item.zValue(),
                "deadline": item.deadline.isoformat() if item.deadline else None,
                "deadline_set_at": (
                    item._deadline_set_at.isoformat()
                    if getattr(item, "_deadline_set_at", None)
                    else None
                ),
            }
            items.append(entry)

    
        # File items (GraphicsFileItem)
        try:
            # `GraphicsFileItem` stores .file_path attribute in your vgraphicsscene
            if hasattr(item, "file_path"):
                fp = getattr(item, "file_path")
                rel = None
                if fp:
                    # if it's already inside this notebook folder, keep relative path
                    rel = _copy_asset(fp, assets)
                entry = {
                    "type": "file",
                    "file": rel,                         # PNG im assets/images
                    "original_path": getattr(item, "original_path", None),  # 🔥 NEU
                    "x": item.x(),
                    "y": item.y(),
                    "z": item.zValue(),
                    "w": item.pixmap().width() if item.pixmap() else None,
                    "h": item.pixmap().height() if item.pixmap() else None,
                }
                items.append(entry)
                continue
        except Exception:
            pass

        # Fallback: store bounding rect and type name
        try:
            items.append({
                "type": "unknown",
                "class": item.__class__.__name__,
                "x": item.x(),
                "y": item.y(),
                "z": item.zValue()
            })
        except Exception:
            pass

    payload = {
        "items": items,
        "canvas": "canvas.png" if canvas_fn else None
    }
    return json.dumps(payload, ensure_ascii=False)

def deserialize_scene(scene, json_str: str, nb_path: str, main_window=None):
    """Clear scene and re-create items. nb_path is the notebook folder (string)."""
    nb_path = Path(nb_path)
    data = {}
    try:
        data = json.loads(json_str or "{}")
    except Exception:
        data = {}

    #scene.undo_stack.setEnabled(False)
    #scene.undo_stack.clear()

    for item in list(scene.items()):
        if hasattr(scene, "canvas_item") and item is scene.canvas_item:
            continue
        scene.removeItem(item)

    # Load canvas pixmap (drawings)
    canvas_file = data.get("canvas")
    if canvas_file:
        canvas_path = nb_path / canvas_file
        if canvas_path.exists():
            pix = QPixmap(str(canvas_path))
            # set canvas_pixmap on scene if attribute exists
            try:
                scene.canvas_pixmap = pix
                # update canvas_item pixmap
                try:
                    scene.canvas_item.setPixmap(pix)
                except Exception:
                    pass
            except Exception:
                pass

    for it in data.get("items", []):
        t = it.get("type")
        if t == "text":
            ti = CanvasTextItem("", start_edit=False)
            ti.setPos(float(it.get("x", 0)), float(it.get("y", 0)))

            if "html" in it:
                ti.setHtml(it["html"])
            else:
                ti.setPlainText(it.get("text", ""))


            
            # deadline: you must parse/assign for your CanvasTextItem if attribute exists
            deadline = it.get("deadline")
            if deadline:
                try:
                    ti.deadline = datetime.datetime.fromisoformat(deadline)
                except Exception:
                    pass

            deadline_set_at = it.get("deadline_set_at")
            if deadline_set_at:
                try:
                    ti._deadline_set_at = datetime.datetime.fromisoformat(deadline_set_at)
                except Exception:
                    pass
            scene.addItem(ti)
            continue

        if t == "file":
            rel = it.get("file")

            if rel:
                # Normalisiere den Pfad und baue den korrekten Pfad zu assets/images
                filename = Path(rel).name  # nur Dateiname
                src = nb_path / "assets" / "images" / filename

                if src.exists():
                    pix = QPixmap(str(src))
                    try:
                        gfi = GraphicsFileItem(
                            pix,
                            file_path=str(src),
                            original_path=it.get("original_path"), 
                            asset_id=src.stem
                        )
                        gfi.setPos(float(it.get("x", 0)), float(it.get("y", 0)))
                        gfi.setZValue(-100) 
                        scene.addItem(gfi)
                    except Exception:
                        item = scene.addPixmap(pix)
                        item.setPos(float(it.get("x", 0)), float(it.get("y", 0)))
                        item.setZValue(-100) 
            continue

        continue

