import os
import shutil
import sys

# 导入补丁基本数据
from data import appInfo


if __name__ == '__main__':
    print("\n[Info]\033[35m初始化数据\033[0m")
    flag = False
    # 所有补丁安装器源码信息
    game_list = [
        ("update", "update", "2.0"),
        ("app", appInfo.app_name, appInfo.ver)
    ]
    cmd = "@echo off\nchcp 65001\n\ncd %~dp0\n\n"
    print("[Info]\033[35m数据初始化完成\033[0m")
    print("[Info]\033[35m清理历史编译\033[0m")
    if os.path.exists(os.path.join(os.path.abspath("."), "dist")):
        shutil.rmtree(os.path.join(os.path.abspath("."), "dist"))
    print("[Info]\033[35m正在初始化编译脚本\033[0m")
    for name, title, ver in game_list:
        add = ""
        print(name)
        if name != "update":
            # add += ' --add-data="update.data:."'
            add += ' --add-data="sources\\*:.\\sources"'
            add += ' --add-data="plugins\\*:.\\plugins"'
            add += ' --windowed'
        cmd += f"..\\repo_launcher\\.venv\\Scripts\\pyinstaller.exe -F {name}.py{add} -n {title.replace(' ', '_')} -i sources\\timer.ico\n"
    print("[Info]\033[35m正在构建编译脚本\033[0m")
    with open("build.cmd", "w", encoding="utf8") as f:
        f.write(f'{cmd}')
        f.close()
    print("[Info]\033[35m编译脚本构建完成\033[0m")

    print("[Info]\033[35m开始执行编译\033[0m")
    os.system("build.cmd")
    print("[Info]\033[32m编译完成\033[0m")
    print("[Info]\033[35m正在创建更新补丁\033[0m")
    if not os.path.exists(os.path.join(os.path.abspath("."), ".release_build")):
        os.makedirs(os.path.join(os.path.abspath("."), ".release_build"))
    if os.path.exists(f"dist/{appInfo.app_name}.exe"):
        os.rename(f"dist/{appInfo.app_name}.exe", f"dist/{appInfo.ver}")
    shutil.make_archive(os.path.join(os.path.abspath("."), ".release_build", f"{appInfo.ver}_update.data"), 'zip', os.path.join(os.path.abspath("."), "dist"))
    if os.path.exists(os.path.join(os.path.abspath("."), ".release_build", f"{appInfo.ver}_update.data.zip")):
        os.rename(os.path.join(os.path.abspath("."), ".release_build", f"{appInfo.ver}_update.data.zip"), os.path.join(os.path.abspath("."), ".release_build", f"{appInfo.ver}_update.data"))
        print("[Info]\033[32m更新补丁创建完成\033[0m")
    else:
        print("[Info]\033[32m更新补丁创建失败\033[0m")
    print("[Info]\033[35m清理编译脚本\033[0m")
    os.remove("build.cmd")
    print("[Info]\033[32m编译脚本清理完成\033[0m")

    if os.path.exists("build"):
        print("[Info]\033[35m清理构建缓存\033[0m")
        shutil.rmtree("build")
        os.system("del .\\*.spec")
        print("[Info]\033[32m构建缓存清理完成\033[0m")

    print(f"\033[7{';'}{'32' if flag else '35'}m   END   \033[0m")
    sys.exit(0)
