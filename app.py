from PyQt6.QtWidgets import QApplication

from ui.main import mainWindow
from lib.core import *


class TimerApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        # 初始化应用程序
        # 检查必要目录
        if os.path.exists(os.path.join(run_path, "update.exe")):
            os.remove(os.path.join(run_path, "update.exe"))
        if not os.path.exists(config_path):
            os.makedirs(config_path)
        # 设置共享内存的key
        self.shared_memory = QSharedMemory(self_uuid)

        if self.shared_memory.attach():
            # 如果已经附加到共享内存，说明程序已经在运行
            self.is_running = True
        else:
            # 创建共享内存
            self.shared_memory.create(1)
            self.is_running = False


def init_ui():
    app = TimerApplication(sys.argv)
    # 已有实例运行时直接退出新实例
    if app.is_running:
        sys.exit(1)
    w = mainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    init_log()
    init_ui()
