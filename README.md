# Timer

一个简单的 Windows 桌面倒计时工具，支持全局快捷键、悬浮窗和自动更新。

A simple Windows desktop countdown timer with global hotkeys, a floating window, and automatic updates.

## 功能特性 | Features

- 倒计时开始、暂停、继续和停止
- 自定义倒计时时间
- 全局快捷键控制
- 默认快捷键：`F8` 开始/暂停，`F9` 停止
- 独立悬浮窗显示剩余时间
- 倒计时结束时发送系统通知
- 支持切换更新通道并检查新版本
- 记录运行日志

---

- Start, pause, resume, and stop the countdown
- Customize the countdown duration
- Control the timer with global hotkeys
- Default hotkeys: `F8` to start/pause and `F9` to stop
- Optional floating window showing the remaining time
- System notification when the countdown finishes
- Update-channel switching and update checking
- Runtime log files

## 使用方式 | Usage

### 使用发布版本 | Use a release build

1. 从 GitHub Releases 下载 `Timer.exe`。
2. 双击运行程序。
3. 通过主窗口设置时间并点击“开始”。
4. 如需后台显示时间，可在菜单中打开“悬浮窗”。
5. 在“热键设置”中修改全局快捷键；修改后关闭设置窗口即可生效。

---

1. Download `Timer.exe` from GitHub Releases.
2. Double-click the executable to launch the application.
3. Set the duration in the main window and click **Start**.
4. Enable **Floating Window** from the menu when you want the remaining time to stay visible.
5. Open **Hotkey Settings** to customize global hotkeys. Changes take effect after closing the settings window.

### 从源码运行 | Run from source

本项目面向 Windows，建议使用 Python 3.11 或更高版本。

This project targets Windows. Python 3.11 or newer is recommended.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install PyQt6 psutil requests pynput
python app.py
```

如果 PowerShell 禁止执行脚本，可以直接使用虚拟环境中的 Python：

If PowerShell execution policy prevents activation, run the application directly with the virtual environment's Python:

```powershell
.venv\Scripts\python.exe app.py
```

## 快捷键 | Hotkeys

| 操作 Action | 默认快捷键 Default |
| --- | --- |
| 开始/暂停 Start/Pause | `F8` |
| 停止 Stop | `F9` |

快捷键可以在应用的“热键设置”窗口中重新录制和保存。

Hotkeys can be recorded and saved again from the application's **Hotkey Settings** window.

## 构建 | Build

安装构建依赖：

Install the build dependencies:

```powershell
python -m pip install PyQt6 psutil requests pynput pyinstaller
```

运行构建脚本会生成更新包，不负责生成独立的主程序：

Running `build.py` creates the update package; it is not the standalone application build:

```powershell
python build.py
```

GitHub Actions 只构建独立的 `Timer.exe`，并将其与本文件打包成 `${app_name}_${ver}.zip`；主分支推送或手动运行工作流成功后，会自动创建对应版本的 GitHub Release。更新包需要在本地运行 `build.py` 生成：

GitHub Actions only builds the standalone `Timer.exe`, packages it together with this README as `${app_name}_${ver}.zip`, and automatically creates the corresponding GitHub Release after a successful push to the main branch or a manual workflow run. The update package must be generated locally with `build.py`:

- `.release_build/Timer.exe`
- `.release_build/Timer_v6.0.2609.11.4.zip`

## 日志与配置 | Logs and Configuration

应用配置保存在 `Timer/config/gui.json`，运行日志保存在 `Timer/logs/`。

Application settings are stored in `Timer/config/gui.json`, and runtime logs are stored in `Timer/logs/`.

## 系统要求 | Requirements

- Windows 10/11
- x64 Windows recommended
- Python 3.11+ when running from source
- Windows permission to listen for global keyboard events

## License

请参阅 [LICENSE](LICENSE)。

See [LICENSE](LICENSE) for license information.
