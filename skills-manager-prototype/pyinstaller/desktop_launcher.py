"""Skills Manager 桌面应用 — PyInstaller/flet pack 启动入口。"""

import sys
from pathlib import Path

# 确保 src/ 和 desktop/ 在 sys.path 中
_project_root = Path(__file__).parent
_src = _project_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from desktop.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
