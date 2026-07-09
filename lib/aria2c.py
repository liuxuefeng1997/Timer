import subprocess

from lib.core import *


class Aria2cDownload(QThread):
    download = pyqtSignal(dict)
    complete = pyqtSignal(bool, float, str)
    isStart = pyqtSignal(bool)
    add_status = pyqtSignal(str)

    def __init__(self, uri, keys, _dir=run_path, rpc_host='localhost', rpc_port=6897, rpc_secret=None, isUpdate=False):
        super(Aria2cDownload, self).__init__()

        self.curr_key = keys if isUpdate else ""
        self.keys = keys if isinstance(keys, list) else [keys]
        self.uri = uri
        self.dir = _dir
        self._is_running = True
        self.current_download_index = 0
        self.start_time = None

        # RPC配置
        self.rpc_host = rpc_host
        self.rpc_port = rpc_port
        self.rpc_secret = rpc_secret
        self.rpc_url = f'http://{rpc_host}:{rpc_port}/jsonrpc'

        # 下载状态跟踪
        self.active_downloads = {}
        self.completed_downloads = {}

    def run(self):
        self.start_time = time.time()

        # 检查RPC服务是否可用
        if not self.check_rpc_connection():
            self.sendComplete(False, 0, self.curr_key)
            return

        # 依次添加下载任务
        for i, key in enumerate(self.keys):
            if not self._is_running:
                break

            self.current_download_index = i
            self.download_file(key)

        # 监控下载进度
        self.monitor_downloads()

    def check_rpc_connection(self):
        """检查RPC连接是否正常"""
        try:
            response = self.rpc_call('aria2.getVersion')
            logging.info(f"[Aria2] 连接到aria2c RPC服务成功，版本: {response.get('version', '未知')}")
            return True
        except Exception as e:
            logging.error(f"[Aria2] 连接aria2c RPC服务失败: {e}")
            return False

    def rpc_call(self, method, params=None):
        """发送RPC调用"""
        if params is None:
            params = []

        # 如果有RPC密钥，添加到参数中
        if self.rpc_secret:
            params = [f"token:{self.rpc_secret}"] + params

        payload = {
            'jsonrpc': '2.0',
            'id': str(time.time()),
            'method': method,
            'params': params
        }

        try:
            response = requests.post(
                self.rpc_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            if 'error' in result:
                logging.error(f"[Aria2] RPC调用错误: {result['error']}")
                raise Exception(f"RPC错误: {result['error']}")

            return result.get('result')
        except requests.exceptions.RequestException as e:
            logging.error(f"[Aria2] RPC请求失败: {e}")
            raise

    def send_add_status(self, status: str):
        self.add_status.emit(status)

    def download_file(self, key):
        """添加下载任务到aria2c"""
        try:
            self.sendStart(True)

            download_url = f'{self.uri}{key}'

            # 下载参数
            options = {
                'dir': self.dir,
                'out': key,
                'max-connection-per-server': '16',
                'split': '16',
                'min-split-size': '1M',
                'max-tries': '5',
                'retry-wait': '3',
                'timeout': '30',
                'connect-timeout': '10',
                'check-certificate': 'false',
                'allow-overwrite': 'true',
                'auto-file-renaming': 'false'
            }

            # 添加下载任务
            gid = self.rpc_call('aria2.addUri', [[download_url], options])

            if gid:
                self.active_downloads[gid] = {
                    'key': key,
                    'start_time': time.time(),
                    'last_progress': 0
                }
                logging.info(f"[Aria2] 已添加下载任务: {key}, GID: {gid}")
                self.send_add_status(f"添加更新队列 {key}")
            else:
                raise Exception("无法获取任务GID")

        except Exception as e:
            logging.error(f"[Aria2] 添加下载任务失败: {e}")
            self.sendComplete(False, 0, self.curr_key)

    def monitor_downloads(self):
        """监控所有下载任务的进度"""
        while self._is_running and (self.active_downloads or self.current_download_index < len(self.keys) - 1):
            try:
                # 获取所有活动任务的状态
                gids_to_remove = []
                for gid, download_info in self.active_downloads.items():
                    if not self._is_running:
                        break

                    # key = download_info['key']
                    try:
                        # 获取任务状态
                        status = self.rpc_call('aria2.tellStatus', [gid])
                        if status:
                            self.process_download_status(gid, download_info, status)
                            # 检查是否完成
                            if status['status'] in ['complete', 'error']:
                                gids_to_remove.append(gid)
                                self.handle_download_completion(download_info, status)

                    except Exception as e:
                        logging.error(f"[Aria2] 获取任务状态失败 {gid}: {e}")
                        continue

                # 移除已完成的任务
                for gid in gids_to_remove:
                    if gid in self.active_downloads:
                        del self.active_downloads[gid]

                # 等待一段时间后再次检查
                if self._is_running and self.active_downloads:
                    time.sleep(1)  # 1秒间隔

            except Exception as e:
                logging.error(f"[Aria2] 监控下载进度出错: {e}")
                time.sleep(2)  # 出错时等待2秒再重试

        # 所有下载完成
        try:
            if self._is_running:
                total_time = time.time() - self.start_time
                success_count = len([k for k in self.completed_downloads if self.completed_downloads[k]])

                if success_count == len(self.keys):
                    self.sendComplete(True, total_time, self.curr_key)
                else:
                    self.sendComplete(False, total_time, self.curr_key)
        except Exception as e:
            logging.error(e)

    def process_download_status(self, gid, download_info, status):
        """处理下载状态并发送进度信号"""
        key = download_info['key']

        try:
            # 解析下载信息
            total_length = int(status.get('totalLength', 0))
            completed_length = int(status.get('completedLength', 0))
            download_speed = int(status.get('downloadSpeed', 0))

            # 计算进度百分比
            if total_length > 0:
                complete_percent = (completed_length / total_length) * 100
            else:
                complete_percent = 0

            # 只有当进度有显著变化时才发送信号
            if (abs(complete_percent - download_info['last_progress']) >= 1 or
                    complete_percent == 100 or
                    complete_percent == 0):

                self.sendProgress({
                    "key": key,
                    "size": completed_length,
                    "content_size": total_length,
                    "complete": complete_percent,
                    "speed": download_speed,
                    "current_file": key,
                    "total_files": len(self.keys),
                    "current_index": self.current_download_index + 1,
                    "gid": gid,
                    "status": status['status']
                })

                download_info['last_progress'] = complete_percent

        except Exception as e:
            logging.error(f"[Aria2] 处理下载状态失败 {gid}: {e}")

    def handle_download_completion(self, download_info, status):
        """处理下载完成"""
        key = download_info['key']
        output_file = os.path.join(self.dir, key)

        if status['status'] == 'complete' and os.path.exists(output_file):
            logging.info(f"[Aria2] 下载完成: {key}")
            self.completed_downloads[key] = True
        else:
            error_code = status.get('errorCode', '未知错误')
            error_message = status.get('errorMessage', '下载失败')
            logging.error(f"[Aria2] 下载失败 {key}: {error_code} - {error_message}")
            self.completed_downloads[key] = False

    def stop_download(self):
        """停止所有下载任务"""
        self._is_running = False

        # 停止所有活动的下载任务
        for gid in list(self.active_downloads.keys()):
            try:
                self.rpc_call('aria2.remove', [gid])
                logging.info(f"[Aria2] 已停止下载任务: {gid}")
            except Exception as e:
                logging.error(f"[Aria2] 停止下载任务失败 {gid}: {e}")

    def pause_download(self, gid=None):
        """暂停下载任务"""
        try:
            if gid:
                # 暂停指定任务
                self.rpc_call('aria2.pause', [gid])
            else:
                # 暂停所有任务
                self.rpc_call('aria2.pauseAll')
        except Exception as e:
            logging.error(f"[Aria2] 暂停下载失败: {e}")

    def resume_download(self, gid=None):
        """恢复下载任务"""
        try:
            if gid:
                # 恢复指定任务
                self.rpc_call('aria2.unpause', [gid])
            else:
                # 恢复所有任务
                self.rpc_call('aria2.unpauseAll')
        except Exception as e:
            logging.error(f"[Aria2] 恢复下载失败: {e}")

    def get_global_stat(self):
        """获取全局统计信息"""
        try:
            return self.rpc_call('aria2.getGlobalStat')
        except Exception as e:
            logging.error(f"[Aria2] 获取全局统计失败: {e}")
            return None

    def sendProgress(self, info: dict):
        self.download.emit(info)

    # 如果为单文件（即下载本体更新补丁），curr_key 返回当前 key 否则返回空文本
    def sendComplete(self, event: bool, times: float, curr_key: str):
        self.complete.emit(event, times, curr_key)

    def sendStart(self, event: bool):
        self.isStart.emit(event)


class Aria2cManager(QThread):
    status_changed = pyqtSignal(bool, str)  # 运行状态, 状态信息
    rpc_ready = pyqtSignal(bool)  # RPC服务是否就绪

    def __init__(self, rpc_port=6800, rpc_secret=None, config_file=None):
        super().__init__()
        self.rpc_port = rpc_port
        self.rpc_secret = rpc_secret
        self.config_file = config_file
        self.aria2c_process = None
        self._is_running = True
        self.aria2c_path = aria2_path

    def run(self):
        """主线程运行"""
        if not self.aria2c_path:
            self.status_changed.emit(False, "未找到aria2c可执行文件")
            self.rpc_ready.emit(False)
            return

        # 先检查是否已有aria2c进程在运行
        if self.is_aria2c_running():
            logging.info("[Aria2] 检测到已有aria2c进程在运行")
            if self.wait_for_rpc_ready():
                self.status_changed.emit(True, "连接到现有aria2c RPC服务")
                self.rpc_ready.emit(True)
                return
            else:
                logging.warning("[Aria2] 现有aria2c进程未启用RPC，将启动新进程")

        # 启动aria2c进程
        if self.start_aria2c():
            self.status_changed.emit(True, "aria2c启动成功")
            # 等待RPC服务就绪
            if self.wait_for_rpc_ready():
                self.rpc_ready.emit(True)
                self.monitor_aria2c_process()
            else:
                self.status_changed.emit(False, "aria2c RPC服务启动失败")
                self.rpc_ready.emit(False)
        else:
            self.status_changed.emit(False, "aria2c启动失败")
            self.rpc_ready.emit(False)

    def start_aria2c(self):
        """启动aria2c进程"""
        try:
            # 构建启动命令
            cmd = self.build_aria2c_command()

            logging.info(f"[Aria2] 启动aria2c命令: {' '.join(cmd)}")

            # 启动进程
            self.aria2c_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                # 隐藏控制台窗口（Windows）
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # 等待进程启动
            time.sleep(2)

            if self.aria2c_process.poll() is not None:
                # 进程已退出
                stderr = self.aria2c_process.stderr.read()
                logging.error(f"[Aria2] aria2c启动失败: {stderr}")
                return False

            logging.info(f"[Aria2] aria2c进程已启动，PID: {self.aria2c_process.pid}")
            return True

        except Exception as e:
            logging.error(f"[Aria2] 启动aria2c时发生错误: {e}")
            return False

    def build_aria2c_command(self):
        """构建aria2c启动命令"""
        cmd = [self.aria2c_path]

        # 如果指定了配置文件，使用配置文件
        if self.config_file and os.path.exists(self.config_file):
            cmd.extend(["--conf-path", self.config_file])
        else:
            # 使用命令行参数配置
            cmd.extend([
                "--enable-rpc=true",
                f"--rpc-listen-port={self.rpc_port}",
                "--rpc-listen-all=false",
                "--rpc-allow-origin-all=true",
                "--rpc-max-request-size=10M",
                # 下载设置
                "--max-connection-per-server=16",
                "--split=16",
                "--min-split-size=1M",
                "--max-tries=5",
                "--retry-wait=3",
                "--timeout=30",
                "--connect-timeout=10",
                "--check-certificate=false",
                "--allow-overwrite=true",
                "--auto-file-renaming=false",
                # 日志设置
                "--console-log-level=warn",
                "--quiet"
            ])

            # 如果设置了RPC密钥
            if self.rpc_secret:
                cmd.append(f"--rpc-secret={self.rpc_secret}")

        return cmd

    def wait_for_rpc_ready(self, timeout=30):
        """等待RPC服务就绪"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.check_rpc_connection():
                logging.info("[Aria2] aria2c RPC服务已就绪")
                return True
            time.sleep(1)

        logging.error("[Aria2] 等待RPC服务就绪超时")
        return False

    def check_rpc_connection(self):
        """检查RPC连接"""
        try:
            url = f'http://localhost:{self.rpc_port}/jsonrpc'
            payload = {
                'jsonrpc': '2.0',
                'id': 'check_connection',
                'method': 'aria2.getVersion',
                'params': []
            }

            response = requests.post(
                url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                return 'result' in result

        except Exception as e:
            logging.error(e)
            return False

        return False

    def is_aria2c_running(self):
        """检查aria2c进程是否在运行"""
        try:
            # 检查我们启动的进程
            if self.aria2c_process and self.aria2c_process.poll() is None:
                return True

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

        return False

    def monitor_aria2c_process(self):
        """监控aria2c进程状态"""
        while self._is_running and self.aria2c_process:
            if self.aria2c_process.poll() is not None:
                # 进程已退出
                return_code = self.aria2c_process.returncode
                stdout, stderr = self.aria2c_process.communicate()

                logging.warning(f"[Aria2] aria2c进程意外退出，返回码: {return_code}")
                if stderr:
                    logging.error(f"[Aria2] aria2c错误输出: {stderr}")

                self.status_changed.emit(False, f"aria2c进程已退出 (代码: {return_code})")
                self.rpc_ready.emit(False)
                break

            time.sleep(2)

    def stop_aria2c(self):
        """停止aria2c进程"""
        self._is_running = False

        try:
            # 首先尝试优雅关闭
            if self.aria2c_process and self.aria2c_process.poll() is None:
                logging.info("[Aria2] 正在停止aria2c进程...")

                # 发送shutdown命令到RPC
                try:
                    self.send_shutdown_command()
                    time.sleep(2)
                except:
                    pass

                # 终止进程
                self.aria2c_process.terminate()

                # 等待进程结束
                try:
                    self.aria2c_process.wait(timeout=10)
                    logging.info("[Aria2] aria2c进程已正常停止")
                except subprocess.TimeoutExpired:
                    # 强制终止
                    logging.warning("[Aria2] 强制终止aria2c进程")
                    self.aria2c_process.kill()
                    self.aria2c_process.wait()

            # 清理
            self.aria2c_process = None
            self.status_changed.emit(False, "aria2c已停止")

        except Exception as e:
            logging.error(f"[Aria2] 停止aria2c时发生错误: {e}")

    def send_shutdown_command(self):
        """通过RPC发送关闭命令"""
        try:
            url = 'http://localhost:'f'{self.rpc_port}/jsonrpc'
            payload = {
                'jsonrpc': '2.0',
                'id': 'shutdown',
                'method': 'aria2.shutdown',
                'params': []
            }

            if self.rpc_secret:
                payload['params'] = [f"token:{self.rpc_secret}"]

            requests.post(
                url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
        except Exception as e:
            logging.debug(f"[Aria2] 通过RPC关闭aria2c失败: {e}")

    def get_rpc_config(self):
        """获取RPC配置信息"""
        return {
            'host': 'localhost',
            'port': self.rpc_port,
            'secret': self.rpc_secret
        }

    def restart_aria2c(self):
        """重启aria2c服务"""
        logging.info("[Aria2] 重启aria2c服务...")
        self.stop_aria2c()
        time.sleep(2)
        self._is_running = True
        self.start()
