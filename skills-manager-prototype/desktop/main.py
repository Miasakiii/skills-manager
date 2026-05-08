"""Skills Manager 桌面应用 — 主入口。

运行方式（在 skills-manager-prototype 目录下）：
    python -m desktop.main
"""

from __future__ import annotations

import flet as ft

from .app import App


def main(page: ft.Page):
    app = App()
    app.build(page)


if __name__ == "__main__":
    ft.run(main)
