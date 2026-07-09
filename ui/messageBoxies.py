from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from data.appInfo import *


class MessageBox_ButtonType:
    Yes = 0
    No = 1
    Retry = 2
    Hidden = 3


class MessageBox_Exit(QDialog):
    def __init__(self, _parent):
        super(MessageBox_Exit, self).__init__(parent=_parent)
        self.user_choice = None
        self.remember_choice = False

        self.setWindowTitle(app_name)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(200, 130)
        self.label = QLabel(self)
        self.label.setText("确定要退出吗？")
        self.label.setGeometry(5, 5, 200, 72)
        self.label.setWordWrap(True)  # 启用自动换行
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.checkBox = QCheckBox(self)
        self.checkBox.setText("记住我的选择")
        self.checkBox.setGeometry(5, 80, 200, 24)

        self.yesButton = QPushButton(self)
        self.yesButton.setText("确定")
        self.yesButton.clicked.connect(lambda: self.send(MessageBox_ButtonType.Yes, self.checkBox.isChecked()))
        self.yesButton.setGeometry(5, 104, 60, 24)
        self.noButton = QPushButton(self)
        self.noButton.setText("取消")
        self.noButton.clicked.connect(lambda: self.send(MessageBox_ButtonType.No, self.checkBox.isChecked()))
        self.noButton.setGeometry(70, 104, 60, 24)
        self.hideButton = QPushButton(self)
        self.hideButton.setText("隐藏")
        self.hideButton.clicked.connect(lambda: self.send(MessageBox_ButtonType.Hidden, self.checkBox.isChecked()))
        self.hideButton.setGeometry(135, 104, 60, 24)

    def exec(self):
        """
        执行对话框并返回用户选择

        Returns:
            tuple: (button_type, remember_choice)
            button_type: MessageBox_ButtonType 枚举值
            remember_choice: bool 是否记住选择
        """
        super().exec()
        return self.get_result()

    def send(self, _type: int, isRemember: bool):
        self.user_choice = _type
        self.remember_choice = isRemember
        self.close()

    def get_result(self):
        return self.user_choice, self.remember_choice
