"""
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt


app = QApplication([])

#setting up Window

window = QMainWindow()

window.setMinimumSize(400,500)
window.setMinimumHeight(400)
window.setMinimumWidth(500)

window.setWindowTitle("Notebook")
window.setWindowIcon(QIcon("testIcon.png"))

#adding widgets

label = QLabel("text kommt hierhin", alignment=Qt.AlignmentFlag.AlignCenter)
font = window.font()
font.setPointSize(17)
font.setBold(True)
label.setFont(font)
window.setCentralWidget(label)


label = QLabel()
label.setPixmap(QPixmap("testIcon.png").scaled(250,250))
label.setAlignment(Qt.AlignmentFlag.AlignCenter)
window.setCentralWidget(label)

window.show()
app.exec()

"""


from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QToolBar, QColorDialog, QFileDialog
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QAction, QBrush
from PyQt6.QtCore import QSize, Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setFixedSize(400,400)
        self.setWindowTitle("Drawing App")

        self.previousPoint = None

        self.label = QLabel()

        self.canvas = QPixmap(QSize(400,400))
        self.canvas.fill(QColor("white"))

        self.pen = QPen()
        self.pen.setColor(QColor("#458cff"))
        self.pen.setWidth(6)
        #pen.setStyle(Qt.PenStyle.DashLine)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        """
        brush = QBrush()
        brush.setColor(QColor("45fffae"))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        """
        

        self.label.setPixmap(self.canvas)
        self.setCentralWidget(self.label)

    def mouseMoveEvent(self, event):
        position = event.pos()
        painter = QPainter(self.canvas)
        painter.setPen(self.pen)

        if self.previousPoint:
            painter.drawLine(self.previousPoint.x(), self.previousPoint.y(), position.x(), position.y())
        else: 
            painter.drawPoint(position.x(),position.y())

        
        painter.end()

        self.label.setPixmap(self.canvas)
        self.previousPoint = position

    def mouseReleaseEvent(self, event):
        self.previousPoint = None
        




       

app = QApplication([])
window = MainWindow()
window.show()
app.exec()


