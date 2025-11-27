from PySide6.QtGui import QUndoCommand

class DrawCommand(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__("Draw Stroke")
        self.scene = scene
        self.item = item

    def undo(self):
        self.scene.removeItem(self.item)

    def redo(self):
        self.scene.addItem(self.item)