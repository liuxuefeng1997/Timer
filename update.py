import getopt
import os.path
import sys
import time

import psutil

from data.appInfo import app_name


def checkRun(process_name):
    for process in psutil.process_iter(['name']):
        if process.info['name'] == process_name:
            return True
    return False


if __name__ == '__main__':
    opts = None
    updateExeName = f"{app_name}.exe"
    try:
        opts, args = getopt.getopt(sys.argv[1:], "n:", ["new"])
    except getopt.GetoptError:
        print()
    if opts:
        for opt, arg in opts:
            if opt in ("-n", "--new"):
                if os.path.exists(arg):
                    print(f"[{app_name} | 更新] 准备开始更新")
                    for s in range(1, 60):
                        if checkRun(updateExeName):
                            print(f"[{app_name} | 更新] 等待程序结束 {s}")
                        else:
                            break
                        time.sleep(1)
                    print(f"[{app_name} | 更新] 正在更新至版本：{arg}")
                    if os.path.exists(updateExeName):
                        os.remove(updateExeName)
                    os.rename(arg, updateExeName)
                    print(f"[{app_name} | 更新] 更新完成，准备重启")
                    for s in reversed(range(1, 4)):
                        print(f"[{app_name} | 更新] 准备重启 {s}")
                        time.sleep(1)
                    os.system(f'start {updateExeName}')
                else:
                    print("更新数据未找到")
            else:
                print("参数错误")
    else:
        print("至少包含 -n, --new 参数")
