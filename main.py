import sys 
from PySide6.QtWidgets import QApplication 
from mainwindow import MainWindow 
from PySide6.QtCore import Qt 
import os


if __name__ == "__main__": 
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_USE_NATIVE_WINDOWS_INK"] = "0"
    app = QApplication(sys.argv) 
    window = MainWindow() 
    window.show() 
    sys.exit(app.exec())



