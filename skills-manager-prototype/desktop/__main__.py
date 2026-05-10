"""桌面应用启动入口。"""

import flet as ft

from .app import App


def main():
    app = App()
    ft.run(app.build)


if __name__ == "__main__":
    main()
