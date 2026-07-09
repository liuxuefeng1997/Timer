from PyQt6.QtCore import *
from PyQt6.QtWidgets import *


class floatWindow(QWidget):
    def __init__(self, _parent):
        super(floatWindow, self).__init__()
        self.setWindowTitle("悬浮窗")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(260, 111)
        self.move(0, 0)
        self.parent = _parent

        self.timer_min_10 = QLabel("0", self)
        self.timer_min_10.setFont(self.parent.timerFont)
        self.timer_min_10.setStyleSheet("color: rgb(0, 255, 0);")
        self.timer_min_10.setGeometry(5, 5, 50, 70)
        self.timer_min_10.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.timer_min_01 = QLabel("3", self)
        self.timer_min_01.setFont(self.parent.timerFont)
        self.timer_min_01.setStyleSheet("color: rgb(0, 255, 0);")
        self.timer_min_01.setGeometry(60, 5, 50, 70)
        self.timer_min_01.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.timer_split = QLabel(":", self)
        self.timer_split.setFont(self.parent.timerFont)
        self.timer_split.setStyleSheet("color: rgb(0, 255, 0);")
        self.timer_split.setGeometry(115, 5, 20, 70)

        self.timer_sec_10 = QLabel("0", self)
        self.timer_sec_10.setFont(self.parent.timerFont)
        self.timer_sec_10.setStyleSheet("color: rgb(0, 255, 0);")
        self.timer_sec_10.setGeometry(140, 5, 50, 70)
        self.timer_sec_10.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.timer_sec_01 = QLabel("0", self)
        self.timer_sec_01.setFont(self.parent.timerFont)
        self.timer_sec_01.setStyleSheet("color: rgb(0, 255, 0);")
        self.timer_sec_01.setGeometry(195, 5, 50, 70)
        self.timer_sec_01.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.Timer = QTimer(self)
        self.Timer.setInterval(100)
        self.Timer.timeout.connect(self.updateUI)
        self.Timer.start()

    def updateUI(self):
        self.timer_min_10.setText(self.parent.timer_min_10.text())
        self.timer_min_01.setText(self.parent.timer_min_01.text())
        self.timer_sec_10.setText(self.parent.timer_sec_10.text())
        self.timer_sec_01.setText(self.parent.timer_sec_01.text())

    def mousePressEvent(self, a0, QMouseEvent=None):
        pass

    def mouseMoveEvent(self, a0, QMouseEvent=None):
        pass

    def mouseReleaseEvent(self, a0, QMouseEvent=None):
        pass
