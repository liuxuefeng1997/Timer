import shutil
import subprocess

from PyQt6.QtGui import *
from lib.aria2c import Aria2cDownload, Aria2cManager
from lib.core import *
from data.api_setting import TencentCloud
from lib.hotkey import KeyCollector
from ui.floatWindow import floatWindow

from ui.messageBoxies import *
from ui.timeSettingWindow import timeSettingWindow
from ui.hotkeySettingWindow import hotkeySettingWindow


class mainWindow(QMainWindow):

    def __init__(self):
        super(mainWindow, self).__init__()
        logging.info("[主窗口] 初始化窗口中")
        logging.info(run_path)
        # 初始化资源=============================================
        self.Icon = QIcon(os.path.join(source_path, "timer.ico"))
        self.checkIcon = QIcon(os.path.join(source_path, "check.png"))
        self.emptyIcon = QIcon()
        font_id = QFontDatabase.addApplicationFont(os.path.join(source_path, "DS-DIGIB.TTF"))
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        font_family = font_families[0]
        self.timerFont = QFont(font_family, 72)
        # 初始化变量=================================================
        self.supported_update_channel = getCOSConfJsonObject(TencentCloud.Update.self_update_channel_list_url)
        self.down = None
        self.aria2c_manager = None
        self.chkUp = None
        self.cleanup_thread = None
        self._isUpdate = False
        self.dev_flag = 0
        self.notification = {}
        self.TimerSec = 0
        # 初始化aria2c================================================
        self.setup_aria2c()
        # 设置窗口标题和大小============================================
        self.setWindowTitle("Timer 倒计时")
        self.setWindowIcon(self.Icon)
        self.resize(255, 134)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(self.width(), self.height())
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        # 初始化托盘图标================================================
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.Icon)
        # 窗口组件=====================================================
        self.timer_min_10 = QLabel("0", self)
        self.timer_min_10.setFont(self.timerFont)
        self.timer_min_10.setGeometry(5, 5, 50, 70)
        self.timer_min_10.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.timer_min_01 = QLabel("3", self)
        self.timer_min_01.setFont(self.timerFont)
        self.timer_min_01.setGeometry(60, 5, 50, 70)
        self.timer_min_01.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.timer_split = QLabel(":", self)
        self.timer_split.setFont(self.timerFont)
        self.timer_split.setGeometry(115, 5, 20, 70)

        self.timer_sec_10 = QLabel("0", self)
        self.timer_sec_10.setFont(self.timerFont)
        self.timer_sec_10.setGeometry(140, 5, 50, 70)
        self.timer_sec_10.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.timer_sec_01 = QLabel("0", self)
        self.timer_sec_01.setFont(self.timerFont)
        self.timer_sec_01.setGeometry(195, 5, 50, 70)
        self.timer_sec_01.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.timer_split.mousePressEvent = self.devMode

        self.startButton = QPushButton(self)
        self.startButton.setText("开始")
        self.startButton.setGeometry(5, 80, 50, 30)
        self.startButton.clicked.connect(self.startTime)

        self.stopButton = QPushButton(self)
        self.stopButton.setText("停止")
        self.stopButton.setGeometry(55, 80, 50, 30)
        self.stopButton.clicked.connect(self.stopTime)

        self.timeSettingButton = QPushButton(self)
        self.timeSettingButton.setText("时间设置")
        self.timeSettingButton.setGeometry(105, 80, 70, 30)
        self.timeSettingButton.clicked.connect(lambda: timeSettingWindow(self).show() if not self.Timer.isActive() else QMessageBox.warning(self, "警告", "请先停止倒计时再更改时间"))

        self.hotkeySettingButton = QPushButton(self)
        self.hotkeySettingButton.setText("热键设置")
        self.hotkeySettingButton.setGeometry(175, 80, 70, 30)
        self.hotkeySettingButton.clicked.connect(lambda: hotkeySettingWindow(self).show())

        self.Timer = QTimer(self)
        self.Timer.setInterval(1000)
        self.Timer.timeout.connect(self.updateTimer)
        # 托盘右键菜单=====================================================
        self.trayMenu = QMenu(self)

        self.showAction = QAction(self)
        self.showAction.setText("隐藏")
        self.showAction.triggered.connect(self.show_tray_menu)
        self.trayMenu.addAction(self.showAction)

        self.trayMenu.addSeparator()

        self.startAction = QAction(self)
        self.startAction.setText("开始")
        self.startAction.triggered.connect(self.startTime)
        self.trayMenu.addAction(self.startAction)

        self.stopAction = QAction(self)
        self.stopAction.setText("停止")
        self.stopAction.triggered.connect(self.stopTime)
        self.trayMenu.addAction(self.stopAction)

        self.trayMenu.addSeparator()

        self.channelMenu = QMenu(self)
        self.channelMenu.setTitle("更新通道")
        self.channelActions = {}
        if self.supported_update_channel:
            for channel, name, enable in self.supported_update_channel:
                self.channelActions[channel] = QAction(self)
                self.channelActions[channel].setText(name)
                self.channelActions[channel].triggered.connect(
                    lambda checked, ch=channel: self.changeChannel(ch)
                )
                self.channelActions[channel].setEnabled(enable)
                self.channelMenu.addAction(self.channelActions[channel])

        self.trayMenu.addMenu(self.channelMenu)
        self.trayMenu.addSeparator()

        self.updateAction = QAction(self)
        self.updateAction.setText("检查更新")
        self.updateAction.triggered.connect(self.buttonUpdate_onClick)
        self.trayMenu.addAction(self.updateAction)

        # 设置菜单-开始==========================================
        self.optionMenu = QMenu(self)
        self.optionMenu.setTitle("更多选项")

        self.floatWindowAction = QAction(self)
        self.floatWindowAction.setText("悬浮窗")
        self.floatWindowAction.triggered.connect(self.floatWindowEnable)
        self.optionMenu.addAction(self.floatWindowAction)

        self.clearMenu = QMenu(self)
        self.clearMenu.setTitle("清除记住")

        self.rememberAction = QAction(self)
        self.rememberAction.setText("关闭选项")
        self.rememberAction.triggered.connect(self.clear_remember)
        self.clearMenu.addAction(self.rememberAction)

        self.posAction = QAction(self)
        self.posAction.setText("窗口位置")
        self.posAction.triggered.connect(self.clear_pos)
        self.clearMenu.addAction(self.posAction)

        self.optionMenu.addMenu(self.clearMenu)
        self.trayMenu.addMenu(self.optionMenu)
        # 设置菜单-结束===========================================
        # 开发菜单-开始==========================================
        self.devMenu = QMenu(self)
        self.devMenu.setTitle("开发")

        self.logDirAction = QAction(self)
        self.logDirAction.setText("日志目录")
        self.logDirAction.triggered.connect(self.openLogDir)
        self.devMenu.addAction(self.logDirAction)

        self.trayMenu.addMenu(self.devMenu)
        # 开发菜单-结束===========================================
        self.aboutAction = QAction(self)
        self.aboutAction.setText("关于")
        self.aboutAction.triggered.connect(self.buttonAbout_onClick)
        self.trayMenu.addAction(self.aboutAction)

        self.trayMenu.addSeparator()

        self.quitAction = QAction(self)
        self.quitAction.setText("退出")
        self.quitAction.triggered.connect(lambda: self.tray_close())
        self.trayMenu.addAction(self.quitAction)

        self.tray.setContextMenu(self.trayMenu)
        self.tray.activated.connect(self._tray)
        self.tray.setToolTip(f"{self.windowTitle()}\n双击：显示/隐藏")
        self.tray.messageClicked.connect(self.on_notification_clicked)
        self.tray.show()
        # 初始化状态栏==================================================
        self.statusBar = QStatusBar(self)
        self.statusBar.setGeometry(0, 111, 255, 22)
        self.statusBar.setSizeGripEnabled(False)
        self.statusBar.showMessage("程序准备中")
        logging.info("[主窗口] 窗口初始化结束")
        # 初始化更新通道================================================
        curr_channel = "release"
        if config.read("gui.json", "update", "channel", "release") in self.channelActions.keys():
            curr_channel = config.read("gui.json", "update", "channel", "release")
        # 初始化并注册热键配置===========================================
        self.hotkey = KeyCollector()
        self.hotkey_enabled = True  # 是否响应全局热键（热键设置窗口打开/录制时临时禁用）
        self.hotkey.combo_triggered.connect(self.onHotkeyTriggered)
        self.register_hotkey_config()
        # 初始化界面中的配置=============================================
        self.changeChannel(curr_channel)
        self.devMenu.menuAction().setVisible(False)
        self.stopTime()  # 按下停止按钮会读取配置，故复用此事件
        # 初始化悬浮窗设置==============================================
        Enable = config.read("gui.json", "floatWindow", "enable", False)
        self.floatWindowAction.setIcon(self.checkIcon) if Enable else self.floatWindowAction.setIcon(self.emptyIcon)
        self.floatWindow = floatWindow(self)
        if Enable:
            self.floatWindow.show()
            logging.info("[悬浮窗] 悬浮窗已启用")
        # 初始化界面位置配置=============================================
        self.init_pos()

    def floatWindowEnable(self):
        Enable = config.read("gui.json", "floatWindow", "enable", False)
        if Enable:
            self.floatWindowAction.setIcon(self.emptyIcon)
            config.write("gui.json", "floatWindow", "enable", False)
            self.floatWindow.hide()
            logging.info("[悬浮窗] 悬浮窗已禁用")
        else:
            self.floatWindowAction.setIcon(self.checkIcon)
            config.write("gui.json", "floatWindow", "enable", True)
            self.floatWindow.show()
            logging.info("[悬浮窗] 悬浮窗已启用")

    def updateTimer(self):
        if self.TimerSec == 0:
            self.stopTime()
            self.send_notification("倒计时结束", "时间到了！", 8000)
            return
        self.TimerSec -= 1
        self.updateUI(self.TimerSec)

    def updateUI(self, Time: int):
        Min = int(Time / 60)
        Sec = Time - (Min * 60)
        self.timer_min_10.setText(f"{get_digit(Min, 1)}")
        self.timer_min_01.setText(f"{get_digit(Min, 0)}")
        self.timer_sec_10.setText(f"{get_digit(Sec, 1)}")
        self.timer_sec_01.setText(f"{get_digit(Sec, 0)}")

    def startTime(self):
        self.stopButton.setEnabled(True)
        self.stopAction.setEnabled(True)
        if self.Timer.isActive():
            self.Timer.stop()
            self.startAction.setText("继续")
            self.startButton.setText("继续")
        else:
            Min = int(f"{self.timer_min_10.text()}{self.timer_min_01.text()}")
            Sec = int(f"{self.timer_sec_10.text()}{self.timer_sec_01.text()}")
            self.TimerSec = Min * 60 + Sec
            self.Timer.start()
            self.startAction.setText("暂停")
            self.startButton.setText("暂停")

    def stopTime(self):
        self.Timer.stop()
        self.startAction.setText("开始")
        self.startButton.setText("开始")
        minute = config.read("gui.json", "time", "min", 3)
        sec = config.read("gui.json", "time", "sec", 0)
        self.timer_min_10.setText(f"{minute}".zfill(2)[0])
        self.timer_min_01.setText(f"{minute}".zfill(2)[1])
        self.timer_sec_10.setText(f"{sec}".zfill(2)[0])
        self.timer_sec_01.setText(f"{sec}".zfill(2)[1])
        self.stopButton.setEnabled(False)
        self.stopAction.setEnabled(False)

    def register_hotkey_config(self):
        """根据 gui.json 的 hotkey 节点注册全局热键（默认：开始=F8，停止=F9）"""
        hotkeys = {
            "start": config.read("gui.json", "hotkey", "start", ["f8"]),
            "stop": config.read("gui.json", "hotkey", "stop", ["f9"]),
        }
        for name, keys in hotkeys.items():
            if self.hotkey.register_combo(name, keys):
                logging.info(f"[热键] 已注册 {name}: {keys}")
            else:
                logging.warning(f"[热键] 注册失败 {name}: {keys}")
        self.hotkey.start()
        logging.info("[热键] 全局热键监听已启动")

    def onHotkeyTriggered(self, name: str):
        """全局热键触发回调"""
        if not self.hotkey_enabled:
            logging.debug(f"[热键] 热键响应已禁用，忽略：{name}")
            return
        logging.debug(f"[热键] 触发：{name}")
        if name == "start":
            self.startTime()
        elif name == "stop":
            self.stopTime()

    def init_pos(self):
        win_x = config.read("gui.json", "position", "x")
        win_y = config.read("gui.json", "position", "y")
        screen_w = self.window().screen().geometry().width()
        screen_h = self.window().screen().geometry().height()
        screens = len(QApplication.screens())
        screen = config.read("gui.json", "screen", "geometry", "0x0,0")
        if win_x and screen == f"{screen_w}x{screen_h}, {screens}":
            self.move(win_x, win_y)
        config.write("gui.json", "screen", "geometry", f"{screen_w}x{screen_h}, {screens}")

    def clear_pos(self):
        config.write("gui.json", "screen", "geometry")
        self.send_notification("选项", "记住的窗口位置已清除，下次启动生效", 3000)

    # 发送系统通知
    def send_notification(self, _title: str, _message: str, _showTime=5000, _noticeLevel="Info", _event=None):
        """
        发送系统通知
        :param _title: 通知标题
        :param _message: 通知内容
        :param _showTime: 显示时间（ms）
        :param _noticeLevel: 通知类型（Info | Warn | Error）
        :param _event: 通知点击事件执行函数
        """
        if _noticeLevel == "Warn":
            _sys_msg_icon = QSystemTrayIcon.MessageIcon.Warning
        elif _noticeLevel == "Error":
            _sys_msg_icon = QSystemTrayIcon.MessageIcon.Critical
        else:
            _sys_msg_icon = QSystemTrayIcon.MessageIcon.Information
        self.notification = {
            "title": _title,
            "msg": _message,
            "event": _event
        }
        logging.info(f"[通知模块] 发送系统通知 {_title}: {_message} | {_noticeLevel}")
        self.tray.showMessage(
            _title,
            _message,
            _sys_msg_icon,
            _showTime  # 显示时长（毫秒）
        )

    # 通知点击事件
    def on_notification_clicked(self):
        def _example():
            pass
        if self.notification:
            logging.info(f"[通知模块] 用户点击通知 {self.notification.get('title')}: {self.notification.get('msg')}")
            func = self.notification.get("event", None)
            if type(func) == type(_example):
                logging.info("[通知模块] 此通知存在事件函数，开始执行")
                try:
                    func()
                except Exception as e:
                    logging.error(f"[通知模块] 执行事件函数出错：{e}")
        self.notification = {}
        logging.info("[通知模块] 通知事件处理结束")

    # 开发入口
    def devMode(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dev_flag >= 9:
                if self.dev_flag == 9:
                    self.statusBar.showMessage("开发菜单已启用，下次启动失效", 3*1000)
                    self.send_notification(app_name, "开发菜单已启用，下次启动失效", 3000)
                    self.devMenu.menuAction().setVisible(True)
                    self.dev_flag += 1
            else:
                if self.dev_flag >= 3:
                    self.statusBar.showMessage(f"再点击 {9 - self.dev_flag} 次，启用开发菜单", 3 * 1000)
                self.dev_flag += 1

    def openLogDir(self):
        logging.info(f"[DEV] 打开日志目录: {log_path} | {self.dev_flag == 9}")
        try:
            os.startfile(log_path)
        except Exception as e:
            logging.debug(f"[DEV] {e}")

    # 切换更新通道
    def changeChannel(self, channel):
        logging.debug(channel)
        for key in self.channelActions:
            if key == channel:
                self.channelActions[key].setIcon(self.checkIcon)
            else:
                self.channelActions[key].setIcon(self.emptyIcon)
        config.write("gui.json", "update", "channel", channel)

    # 检查更新按钮事件
    def buttonUpdate_onClick(self):
        self.checkSelfUpdate(showTip=True)

    # 检查更新
    def checkSelfUpdate(self, showTip=False):
        self.chkUp = checkUpdate(showTip=showTip)
        self.chkUp.newLog.connect(self.updateLog)
        self.chkUp.noUpdate.connect(self.noUpdate)
        self.chkUp.start()

    def noUpdate(self, show):
        if show:
            self.send_notification(app_name, "已是最新版本")
            # QMessageBox.information(self, "更新", '已是最新版本')

    # Aria2c 相关
    # 初始化 aria2c rpc
    def setup_aria2c(self):
        # 创建aria2c管理器
        self.aria2c_manager = Aria2cManager(
            rpc_port=6897
        )

        # 连接信号
        # self.aria2c_manager.status_changed.connect(self.on_aria2c_status_changed)
        self.aria2c_manager.rpc_ready.connect(self.on_rpc_ready)

        # 启动管理器
        self.aria2c_manager.start()

    # aria2c 就绪
    def on_rpc_ready(self, is_ready):
        if is_ready:
            self.statusBar.showMessage("下载引擎就绪", 3000)
            # 更新检查
            self.checkSelfUpdate()

    # 更新检查回调
    def updateLog(self, version, log, channel):
        if channel == "release":
            buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        else:
            buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Ignore
        box = QMessageBox.question(
            self,
            "更新",
            "<p>发现新版本："f"{version}""</p><p>"f"{log}"'</p><p>要现在进行更新吗？</p>',
            buttons
        )
        if box == QMessageBox.StandardButton.Yes:
            self.do_update(version)
        elif box == QMessageBox.StandardButton.Ignore:
            config.write("gui.json", "update", "skip_version", version)

    # 本体更新直接拉起 Aria2 下载
    def do_update(self, version):
        self.down = Aria2cDownload(uri=TencentCloud.Update.self_update_url, keys=f"{version}_update.data", isUpdate=True)
        self.down.isStart.connect(self.onUpdateStart)
        self.down.download.connect(self.onUpdate)
        self.down.complete.connect(self.onUpdateComplete)
        self.down.start()

    # 本体更新开始回调
    def onUpdateStart(self, event):
        self.statusBar.showMessage("开始下载更新")

    # 本体更新进度回调
    def onUpdate(self, progress: dict):
        self.statusBar.showMessage(f"下载：{progress.get('complete'): .2f} %")

    # 本体更新完成回调
    def onUpdateComplete(self, e, t, k: str):
        if e:
            self.statusBar.showMessage(f"更新文件下载完成，用时{t: .2f} 秒")
            if QMessageBox.question(self, "更新", "更新已下载，将自动重启完成更新", QMessageBox.StandardButton.Yes):
                try:
                    self.statusBar.showMessage("开始解压更新")
                    shutil.unpack_archive(os.path.join(run_path, f"{k}"), run_path, 'zip')
                    self.statusBar.showMessage("解压更新完成")
                except Exception as e:
                    logging.error(f"[主窗口] {e}")
                    QMessageBox.question(self, "更新", "更新文件解压失败，请稍后重新检查更新尝试", QMessageBox.StandardButton.Yes)
                    return
            if os.path.exists(os.path.join(run_path, f"{k}")):
                os.remove(os.path.join(run_path, f"{k}"))
            subprocess.Popen(
                f'start "{app_name} | 更新" update.exe -n {k.replace("_update.data", "")}',
                shell=True,
                startupinfo=subprocess.STARTUPINFO(
                    dwFlags=subprocess.STARTF_USESHOWWINDOW,
                    wShowWindow=0
                )
            )
            self._isUpdate = True
            self.close()

    # 托盘退出
    def tray_close(self):
        self._isUpdate = True
        self.close()

    # 清除记住选项
    def clear_remember(self):
        config.write("gui.json", "exit", "remember")
        self.send_notification("选项", "记住的关闭选项已清除", 3000)

    # 重写关闭事件
    def closeEvent(self, event):
        if not self._isUpdate:
            _type = config.read("gui.json", "exit", "remember", 999)
            if _type == 999:
                _type, remember = MessageBox_Exit(self).exec()
                if remember:
                    config.write("gui.json", "exit", "remember", _type)
            if _type == MessageBox_ButtonType.No:
                event.ignore()
                return
            elif _type == MessageBox_ButtonType.Hidden:
                if not self.isHidden():
                    self.show_tray_menu()
                event.ignore()
                return
        self.statusBar.showMessage("正在结束程序")
        pos = self.pos()
        config.write("gui.json", "position", "x", pos.x())
        config.write("gui.json", "position", "y", pos.y())
        self.Timer.stop()
        self.hotkey.stop()
        logging.info("[主窗口] 准备结束程序")
        self.tray = None
        self.cleanup_thread = CleanupThread(self)
        self.cleanup_thread.finished.connect(lambda: self.finalClose(event))
        self.cleanup_thread.start()
        event.ignore()

    def finalClose(self, event):
        logging.info("[主窗口] 主窗口关闭")
        logging.debug(f"[主窗口] 清理后台进程结果：{not self.cleanup_thread.isRunning()}")
        event.accept()
        sys.exit(0)

    # 托盘菜单显示隐藏主程序功能
    def show_tray_menu(self):
        if self.isHidden():
            self.showAction.setText("隐藏")
            self.show()
        else:
            self.showAction.setText("显示")
            self.hide()

    # 托盘菜单鼠标事件
    def _tray(self, reason):
        logging.debug(f'tray-icon: {reason}')
        match f'{reason}':
            case "ActivationReason.DoubleClick":
                self.show_tray_menu()

    # 关于按钮事件
    def buttonAbout_onClick(self):
        QMessageBox.information(self, "关于", '<p>版本: 'f'{ver}''</p>'
                                            "<p>感谢  Lr ʕ ᵔᴥᵔ ʔ 提供的部分功能实现<p>"
                                            '<p>服务器赞助</p><p><a href="https://www.mailx.top/images/wxpay/wxpay.jpeg">微信支付</a> | <a href="https://afdian.com/a/xingKongVersionRX">爱发电</a></p>')
