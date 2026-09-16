import datetime
import hashlib
import json
import logging
import time
import winreg
import psutil
import requests as requests
from PyQt6.QtCore import *

from data.api_setting import TencentCloud
from data.appInfo import ver, app_name
from lib.path import *
from lib.config import Config

run_path = os.getcwd()
config_path = os.path.join(run_path, "Timer", "config")
log_path = os.path.join(run_path, "Timer", "logs")
plugin_path = resource_path("plugins")
source_path = resource_path("sources")
aria2_path = os.path.join(plugin_path, "timer_aria2c.exe")
self_uuid = hashlib.md5(f"{app_name}{run_path}".encode("utf8")).hexdigest()
config = Config(config_path)


def init_log():
    NOW_TIME_WITH_NO_SPACE = time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))
    config.write("gui.json", "log", "level_help", "10 = DEBUG, 20 = INFO, 30 = WARNING, 40 = ERROR, 50 = CRITICAL, 支持以上级别，默认为 INFO")
    logLevel = config.read("gui.json", "log", "level", logging.INFO)
    if getattr(sys, 'frozen', False):
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        logging.basicConfig(
            level=logLevel,
            format='[%(asctime)s][%(levelname)s] %(message)s',
            handlers=[logging.FileHandler(filename=os.path.join(log_path, f'Log_{NOW_TIME_WITH_NO_SPACE}.txt'), mode='w', encoding='utf-8')]
        )
    else:
        logging.basicConfig(
            level=logLevel,
            format='[%(asctime)s][%(levelname)s] %(message)s'
        )


def network_check():
    chk = False
    try:
        requests.get("http://connectivitycheck.platform.hicloud.com/generate_204")
        chk = True
    except Exception as e:
        logging.info(f"[Core] {e}")
    return chk


def readJson(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf8") as f:
            r = json.loads(f.read())
            f.close()
    except FileNotFoundError:
        logging.debug(f"[Core] 文件不存在 {path}")
        r = {}
    return r


def writeJson(path: str, json_object: dict) -> bool:
    try:
        with open(path, "w", encoding="utf8") as f:
            f.write(json.dumps(json_object, ensure_ascii=False, indent=4))
            f.close()
        r = True
    except Exception as e:
        logging.debug(f"[Core] {e}")
        r = False
    return r


def checkRun(process_name):
    for process in psutil.process_iter(['name', 'pid']):
        if process.info['name'] == process_name:
            return process.info['pid']
    return False


def getCOSConfJsonObject(uri: str) -> dict:
    try:
        jsonObject = requests.get(uri).json()
    except Exception as s:
        logging.error(f"[Core] {s}")
        jsonObject = {}
    return jsonObject


def remove_empty_folders(root_dir):
    for root, dirs, _ in os.walk(root_dir, topdown=False):  # 自底向上遍历
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                os.rmdir(dir_path)  # 尝试删除空文件夹
                # print(f"已删除空文件夹: {dir_path}")
            except Exception as e:
                if not run_path:
                    logging.debug(e)
                pass  # 忽略非空文件夹


def generateFilenameWithDatetime(prefix="", suffix="", extension="", include_time=True):
    """
    生成包含当前日期时间的文件名

    参数:
        prefix (str): 文件名前缀
        suffix (str): 文件名后缀
        extension (str): 文件扩展名(不需要加点)
        include_time (bool): 是否包含时间部分

    返回:
        str: 生成的完整文件名
    """
    # 获取当前日期时间
    now = datetime.datetime.now()
    # 格式化日期时间
    if include_time:
        datetime_str = now.strftime("%Y%m%d_%H%M%S")  # 格式: 20230805_143022
    else:
        datetime_str = now.strftime("%Y%m%d")  # 格式: 20230805
    # 构建文件名
    filename = f"{prefix}{datetime_str}{suffix}"
    # 添加扩展名
    if extension:
        filename = f"{filename}.{extension.lstrip('.')}"

    return filename


def get_digit(num, position):
    """
    提取数值的指定位数字
    position: 0=个位, 1=十位, 2=百位, 以此类推
    """
    return (num // (10 ** position)) % 10


class checkUpdate(QThread):
    newLog = pyqtSignal(str, str, str)
    noUpdate = pyqtSignal(bool)

    def __init__(self, showTip=False):
        super(checkUpdate, self).__init__()
        self.showTip = showTip

    def run(self):
        version: dict = getCOSConfJsonObject(TencentCloud.Update.self_update_manifest_url)
        logging.debug(version)
        gui = readJson(os.path.join(config_path, "gui.json"))
        channel = gui.get("channel", "release")
        newVer = version.get(channel, "0")
        newInt = int(newVer.replace("v", "").replace(".", ""))
        oldInt = int(ver.replace("v", "").replace(".", ""))
        if newInt > oldInt:
            skip = gui.get("skip_version", "0")
            skipInt = int(skip.replace("v", "").replace(".", ""))
            show_upTip = False
            if channel == "release":
                show_upTip = True
            else:
                release = version.get("release", "0")
                releaseInt = int(release.replace("v", "").replace(".", ""))
                if newInt > skipInt:
                    show_upTip = True
                else:
                    if releaseInt > oldInt:
                        show_upTip = True
                        newVer = release
                        channel = "release"

            if show_upTip:
                self.sendLog(newVer, version.get(f"updateLog.{channel}", "无更新日志"), channel)
            else:
                logging.info(f"[更新模块] {newVer} 更新已跳过")
                self.sendNoUpdate()
        else:
            self.sendNoUpdate()

    def sendLog(self, version: str, log: str, channel: str):
        self.newLog.emit(version, log, channel)

    def sendNoUpdate(self):
        self.noUpdate.emit(self.showTip)


class CleanupThread(QThread):
    def __init__(self, parent):
        super(CleanupThread, self).__init__()
        self.parent = parent

    def run(self):
        try:
            logging.info("[Core] 进行后台执行清理线程")
            logging.info("[Core] 正在关闭aria2c...")
            if self.parent.aria2c_manager:
                self.parent.aria2c_manager.stop_aria2c()
            pid = checkRun("timer_aria2c.exe")
            if pid:
                psutil.Process(pid).kill()
            logging.info("[Core] 程序已结束")
        except Exception as e:
            logging.error(f"[Core] {e}")
