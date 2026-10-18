"""一键启动 AI 代码可视化工具（后端 + 前端 + 自动打开浏览器）。

用法：
    python start.py        # 命令行启动
    双击 start.bat          # Windows 双击启动

首次运行会自动安装前端依赖（npm install）。Ctrl+C 退出。
"""

import os
import subprocess
import sys
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FRONTEND = os.path.join(ROOT, "frontend")
URL = "http://127.0.0.1:5173"


def main() -> int:
    if not os.path.isdir(os.path.join(FRONTEND, "node_modules")):
        print("首次运行：安装前端依赖（npm install，约 1 分钟）...")
        try:
            subprocess.run("npm install", cwd=FRONTEND, shell=True, check=True)
        except subprocess.CalledProcessError:
            print("依赖安装失败：请确认已安装 Node.js，或手动执行 cd frontend && npm install")
            return 1

    print("启动后端 server (127.0.0.1:8000) ...")
    backend = subprocess.Popen([PY, "-m", "backend.server", "--port", "8000"], cwd=ROOT)

    print("启动前端 dev server (127.0.0.1:5173) ...")
    frontend = subprocess.Popen("npm run dev", cwd=FRONTEND, shell=True)

    time.sleep(3)
    webbrowser.open(URL)
    print(f"已启动：{URL}")
    print("按 Ctrl+C 退出。")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭...")
    finally:
        backend.terminate()
        frontend.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
