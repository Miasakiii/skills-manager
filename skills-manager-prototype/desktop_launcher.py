"""Skills Manager 桌面应用 — flet pack 启动入口。"""
import sys
from pathlib import Path

# 确保 desktop 包可导入（开发和 PyInstaller 环境均适用）
if getattr(sys, "frozen", False):
    # PyInstaller 环境：从打包数据中查找
    _base = Path(sys._MEIPASS)
else:
    _base = Path(__file__).parent

_src = _base / "src"
if str(_src) not in sys.path and _src.is_dir():
    sys.path.insert(0, str(_src))
if str(_base) not in sys.path:
    sys.path.insert(0, str(_base))

from desktop.__main__ import main

if __name__ == "__main__":
    main()
