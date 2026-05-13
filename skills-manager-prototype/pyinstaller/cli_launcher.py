"""PyInstaller 启动入口 — CLI 工具。"""

import sys
from skills_manager.cli import app

if __name__ == "__main__":
    sys.exit(app())
