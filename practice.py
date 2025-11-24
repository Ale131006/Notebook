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
"""
label = QLabel("text kommt hierhin", alignment=Qt.AlignmentFlag.AlignCenter)
font = window.font()
font.setPointSize(17)
font.setBold(True)
label.setFont(font)
window.setCentralWidget(label)
"""

label = QLabel()
label.setPixmap(QPixmap("testIcon.png").scaled(250,250))
label.setAlignment(Qt.AlignmentFlag.AlignCenter)
window.setCentralWidget(label)

window.show()
app.exec()


