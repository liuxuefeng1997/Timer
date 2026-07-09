from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from lib.core import config


class timeSettingWindow(QDialog):
    def __init__(self, _parent):
        super(timeSettingWindow, self).__init__(parent=_parent)
        self.setWindowTitle("时间设置")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.parent = _parent

        # 时间输入框（00:05-59:59）
        self.timeEdit = QTimeEdit(self)
        self.timeEdit.setTimeRange(QTime(0, 0, 5), QTime(0, 59, 59))
        self.timeEdit.setDisplayFormat("mm:ss")
        self.timeEdit.setGeometry(5, 5, 140, 20)

        minute = config.read("gui.json", "time", "min", 3)
        sec = config.read("gui.json", "time", "sec", 0)
        self.timeEdit.setTime(QTime(0, minute, sec))

    def closeEvent(self, e):
        config.write("gui.json", "time", "min", self.timeEdit.time().minute())
        config.write("gui.json", "time", "sec", self.timeEdit.time().second())
        minute = config.read("gui.json", "time", "min", 3)
        sec = config.read("gui.json", "time", "sec", 0)
        self.parent.timer_min_10.setText(f"{minute}".zfill(2)[0])
        self.parent.timer_min_01.setText(f"{minute}".zfill(2)[1])
        self.parent.timer_sec_10.setText(f"{sec}".zfill(2)[0])
        self.parent.timer_sec_01.setText(f"{sec}".zfill(2)[1])

