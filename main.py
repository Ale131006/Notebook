import sys 
from PySide6.QtWidgets import QApplication 
from mainwindow import MainWindow 
from PySide6.QtCore import Qt 


if __name__ == "__main__": 
    QApplication.setAttribute(Qt.AA_CompressTabletEvents, False) 
    QApplication.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTabletEvents, False) 
    app = QApplication(sys.argv) 
    window = MainWindow() 
    window.show() 
    sys.exit(app.exec())


""""Notifications wenn das Programm geschlossen ist"""

"""Sachen speichern"""

