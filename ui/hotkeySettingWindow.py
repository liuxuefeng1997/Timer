import logging

from PyQt6.QtCore import *
from PyQt6.QtWidgets import *

from lib.core import config
from lib.hotkey import normalize_key_name

# 可配置的热键动作：配置项名 -> 界面显示名
HOTKEY_ACTIONS = {"start": "开始", "stop": "停止"}
# 默认热键
DEFAULT_KEYS = {"start": ["f8"], "stop": ["f9"]}
# 修饰键（不允许单独作为热键）
MODIFIER_KEYS = {"ctrl", "shift", "alt", "cmd"}

# 按键显示名称与排序（修饰键优先）
_DISPLAY_NAMES = {
    "ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "cmd": "Win",
    "space": "Space", "enter": "Enter", "esc": "Esc", "tab": "Tab",
    "backspace": "Backspace", "delete": "Delete", "insert": "Insert",
    "home": "Home", "end": "End",
    "page_up": "Page Up", "page_down": "Page Down",
    "up": "↑", "down": "↓", "left": "←", "right": "→",
    "print_screen": "PrtSc", "scroll_lock": "Scroll Lock", "pause": "Pause",
    "caps_lock": "Caps Lock", "num_lock": "Num Lock",
}
_MOD_ORDER = {"ctrl": 0, "shift": 1, "alt": 2, "cmd": 3}


def _sort_keys(keys) -> list:
    """修饰键排在前面，其余按键按名称排序"""
    return sorted(keys, key=lambda k: (_MOD_ORDER.get(k, 9), k))


def _format_keys(keys) -> str:
    """按键列表转显示文本，如 ['ctrl', 'f8'] -> 'Ctrl + F8'"""
    parts = []
    for key in keys:
        if len(key) == 1:
            parts.append(key.upper())
        elif key.startswith("f") and key[1:].isdigit():
            parts.append(key.upper())
        else:
            parts.append(_DISPLAY_NAMES.get(key, key))
    return " + ".join(parts)


class hotkeySettingWindow(QDialog):
    """热键设置窗口：点击动作按键录制新的组合键，关闭窗口时保存并即时生效"""

    def __init__(self, _parent):
        super(hotkeySettingWindow, self).__init__(parent=_parent)
        self.setWindowTitle("热键设置")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        # 关闭窗口即销毁，避免残留对象继续接收按键事件
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # 固定窗口大小，禁止用户拖拽缩放
        self.setFixedSize(330, 220)

        self._parent_win = _parent
        self._capture_action = None  # 正在录制的动作名（None 表示空闲）
        self._pressed = set()        # 当前按住的键（规范化键名）
        # 待生效的配置（关闭窗口时写入并注册）
        self._pending = {}
        for action in HOTKEY_ACTIONS:
            self._pending[action] = list(
                config.read("gui.json", "hotkey", action, DEFAULT_KEYS[action])
            )

        self._build_ui()
        self._update_all_buttons()
        self._bind_collector()
        # 窗口打开期间暂时禁用全局热键响应，避免录制时误触发开始/停止
        self._parent_win.hotkey_enabled = False

    # UI 构建========================================================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        tip = QLabel("点击下方按钮，然后按下新的按键组合即可修改（按 Esc 取消录制）")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self.key_buttons = {}
        for action, label in HOTKEY_ACTIONS.items():
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            name = QLabel(f"{label}：", row)
            name.setFixedWidth(44)
            button = QPushButton(row)
            button.setMinimumHeight(26)
            # 用 lambda 屏蔽 clicked 信号的 checked 参数
            button.clicked.connect(lambda checked=False, a=action: self._begin_capture(a))
            self.key_buttons[action] = button
            row_layout.addWidget(name)
            row_layout.addWidget(button, 1)
            layout.addWidget(row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        reset_button = QPushButton("恢复默认")
        reset_button.clicked.connect(self._reset_default)
        button_row.addWidget(reset_button)
        layout.addLayout(button_row)

    def _bind_collector(self):
        collector = self._parent_win.hotkey
        if collector:
            collector.key_pressed.connect(self._on_capture_press)

    def _update_all_buttons(self):
        for action in HOTKEY_ACTIONS:
            self.key_buttons[action].setText(_format_keys(self._pending[action]))
        self.status_label.setText("修改后关闭窗口即生效")

    # 录制流程======================================================
    def _begin_capture(self, action):
        if self._capture_action:
            QMessageBox.information(self, "热键设置", "请先完成当前的按键录制")
            return
        logging.info(f"[热键设置] 开始录制: {action}")
        self._capture_action = action
        self._pressed.clear()
        self.key_buttons[action].setText("请按下新的组合键…")
        self.status_label.setText(f"正在录制「{HOTKEY_ACTIONS[action]}」：按下按键组合即可，Esc 取消")

    def _on_capture_press(self, key_str: str):
        if not self._capture_action:
            return
        key_name = normalize_key_name(key_str)
        if key_name == "esc":
            self._cancel_capture()
            return
        # 系统自动重复的连续按下事件直接忽略
        if key_name in self._pressed:
            return
        self._pressed.add(key_name)
        logging.info(f"[热键设置] 按下: {key_str} -> {key_name}, 当前按住={self._pressed}")
        # 一旦按下的键中包含非修饰键，立即完成录制（此时已包含此前按住的修饰键）
        if any(key not in MODIFIER_KEYS for key in self._pressed):
            self._finish_capture()

    def _cancel_capture(self):
        if not self._capture_action:
            return
        action = self._capture_action
        self._capture_action = None
        self._pressed.clear()
        logging.info(f"[热键设置] 取消录制: {action}")
        self.key_buttons[action].setText(_format_keys(self._pending[action]))
        self.status_label.setText("已取消录制，关闭窗口后生效")

    def _finish_capture(self):
        action = self._capture_action
        self._capture_action = None
        keys = _sort_keys(self._pressed)
        self._pressed.clear()
        label = HOTKEY_ACTIONS[action]
        logging.info(f"[热键设置] 录制结束: {action}, 结果={keys}")
        # 校验
        if not keys:
            self.key_buttons[action].setText(_format_keys(self._pending[action]))
            return
        for other, other_keys in self._pending.items():
            if other != action and _sort_keys(other_keys) == keys:
                QMessageBox.warning(self, "热键设置", f"与「{HOTKEY_ACTIONS[other]}」的热键重复，请更换按键")
                self.key_buttons[action].setText(_format_keys(self._pending[action]))
                self.status_label.setText("设置失败，请重试")
                return

        self._pending[action] = keys
        self.key_buttons[action].setText(_format_keys(keys))
        self.status_label.setText(f"已设置「{label}」为 {_format_keys(keys)}，关闭窗口后生效")

    # 其他==========================================================
    def _reset_default(self):
        if self._capture_action:
            self._cancel_capture()
        for action in HOTKEY_ACTIONS:
            self._pending[action] = list(DEFAULT_KEYS[action])
        self._update_all_buttons()

    def closeEvent(self, e):
        if self._capture_action:
            self._cancel_capture()
        # 保存配置并重新注册（即时生效）
        for action, keys in self._pending.items():
            config.write("gui.json", "hotkey", action, keys)
        try:
            self._parent_win.register_hotkey_config()
            self._parent_win.hotkey_enabled = True
        except Exception as err:
            logging.error(f"[热键设置] 重新注册失败: {err}")
        e.accept()
