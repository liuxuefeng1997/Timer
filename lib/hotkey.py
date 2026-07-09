import time
from typing import List, Dict, Optional, Set, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from pynput import keyboard as pynput_keyboard

# 按键别名（用于组合键匹配，统一左右修饰键等）
_KEY_ALIASES = {
    "control": "ctrl", "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "shift_l": "shift", "shift_r": "shift",
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt", "menu": "alt",
    "cmd_l": "cmd", "cmd_r": "cmd", "win": "cmd", "windows": "cmd",
    "win_l": "cmd", "win_r": "cmd",
}


def normalize_key_name(name: str) -> str:
    """将任意按键名称（pynput 事件或配置）规范化为用于匹配的键名"""
    s = str(name).lower().strip()
    return _KEY_ALIASES.get(s, s)


class KeyCollector(QObject):
    """按键采集器 - 全局键盘监听与录制"""

    # 信号
    key_pressed = pyqtSignal(str)      # 按键按下信号，参数：按键名称
    key_released = pyqtSignal(str)     # 按键释放信号，参数：按键名称
    combo_triggered = pyqtSignal(str)  # 组合键触发信号，参数：组合键名称

    def __init__(self):
        super().__init__()
        # 监听器
        self._listener = None
        self._running = False

        # 按键状态（存储规范化后的键名，便于匹配普通字符与左右修饰键）
        self._pressed_keys: Set[str] = set()

        # 录制相关
        self._recorded_keys: List[Dict] = []
        self._is_recording: bool = False
        self._start_time: Optional[float] = None

        # 组合键
        self._combo_keys: Dict[str, Set] = {}  # 名称 -> 按键集合
        self._triggered_combos: Set[str] = set()  # 已触发（按下）的组合键，用于边沿触发

        # 事件队列（用于跨线程通信）
        self._event_queue: List[Tuple[str, any]] = []
        self._timer = QTimer()
        self._timer.timeout.connect(self._process_events)
        self._timer.setInterval(50)

    def start(self) -> None:
        """启动键盘监听"""
        if self._running:
            return

        self._running = True
        self._timer.start()
        self._pressed_keys.clear()
        self._triggered_combos.clear()

        self._listener = pynput_keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()

    def stop(self) -> None:
        """停止键盘监听"""
        if not self._running:
            return

        self._running = False
        self._timer.stop()

        if self._listener:
            self._listener.stop()
            self._listener = None

        self._pressed_keys.clear()
        self._triggered_combos.clear()

    def start_recording(self) -> None:
        """开始录制按键"""
        self._is_recording = True
        self._recorded_keys.clear()
        self._start_time = time.time()

    def stop_recording(self) -> List[Dict]:
        """停止录制并返回记录的按键序列"""
        self._is_recording = False
        return self._recorded_keys.copy()

    def clear_recording(self) -> None:
        """清空录制记录"""
        self._recorded_keys.clear()
        self._start_time = None

    def get_recorded_keys(self) -> List[Dict]:
        """获取录制的按键序列"""
        return self._recorded_keys.copy()

    def register_combo(self, name: str, keys: List[str]) -> bool:
        """
        注册组合键

        Args:
            name: 组合键名称
            keys: 按键列表，如 ['ctrl', 'c']

        Returns:
            bool: 注册是否成功
        """
        try:
            key_set = set()
            for key_str in keys:
                key_name = normalize_key_name(key_str)
                if key_name:
                    key_set.add(key_name)

            if key_set:
                self._combo_keys[name] = key_set
                return True
            return False
        except Exception:
            return False

    def unregister_combo(self, name: str) -> bool:
        """注销组合键"""
        if name in self._combo_keys:
            del self._combo_keys[name]
            return True
        return False

    def unregister_all_combos(self) -> None:
        """注销所有组合键"""
        self._combo_keys.clear()

    def get_combos(self) -> Dict[str, Set]:
        """获取所有注册的组合键"""
        return self._combo_keys.copy()

    def is_recording(self) -> bool:
        """检查是否正在录制"""
        return self._is_recording

    def is_running(self) -> bool:
        """检查监听器是否在运行"""
        return self._running

    def _key_to_str(self, key) -> str:
        """将按键对象转换为字符串"""
        try:
            if hasattr(key, 'char') and key.char is not None:
                return key.char
            elif hasattr(key, 'name'):
                return key.name
            else:
                return str(key)
        except:
            return str(key)

    def _on_press(self, key):
        """按键按下事件（在子线程中执行）"""
        if not self._running:
            return

        key_str = self._key_to_str(key)
        current_time = time.time()

        # 添加到按下的键集合（规范化键名）
        self._pressed_keys.add(normalize_key_name(key_str))

        # 录制按键
        if self._is_recording:
            self._recorded_keys.append({
                'type': 'press',
                'key': key_str,
                'time': current_time - self._start_time,
                'timestamp': current_time
            })

        # 检查组合键（边沿触发：组合键从“未全部按下”变为“全部按下”时触发一次，
        # 避免按键自动重复/长按导致的重复触发）
        for combo_name, combo_keys in self._combo_keys.items():
            if combo_name not in self._triggered_combos and combo_keys.issubset(self._pressed_keys):
                self._triggered_combos.add(combo_name)
                self._event_queue.append(('combo', combo_name))

        # 发送按键信号
        self._event_queue.append(('press', key_str))

    def _on_release(self, key):
        """按键释放事件（在子线程中执行）"""
        if not self._running:
            return

        key_str = self._key_to_str(key)
        current_time = time.time()

        # 从按下的键集合中移除（规范化键名）
        self._pressed_keys.discard(normalize_key_name(key_str))

        # 组合键复位：任一成员键被释放后允许再次触发
        for combo_name, combo_keys in self._combo_keys.items():
            if combo_name in self._triggered_combos and not combo_keys.issubset(self._pressed_keys):
                self._triggered_combos.remove(combo_name)

        # 录制按键
        if self._is_recording:
            self._recorded_keys.append({
                'type': 'release',
                'key': key_str,
                'time': current_time - self._start_time,
                'timestamp': current_time
            })

        # 发送按键信号
        self._event_queue.append(('release', key_str))

    def _process_events(self):
        """处理事件队列（在主线程中执行）"""
        while self._event_queue:
            event_type, data = self._event_queue.pop(0)
            if event_type == 'press':
                self.key_pressed.emit(data)
            elif event_type == 'release':
                self.key_released.emit(data)
            elif event_type == 'combo':
                self.combo_triggered.emit(data)
