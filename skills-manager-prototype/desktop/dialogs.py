"""对话框：安装 Skill。"""

from __future__ import annotations

from pathlib import Path

import flet as ft


def build_install_dialog(app) -> ft.AlertDialog:
    async def pick_directory(_):
        path = await ft.FilePicker().get_directory_path()
        if not path:
            return
        app._close_active_dialog()
        try:
            result = app.store.install(Path(path), force=True)
            app._refresh_skills()
            app.show_snack(f"已安装 {result.name} v{result.version}")
            app._update_ui()
        except Exception as ex:
            app.show_snack(f"安装失败: {ex}", error=True)

    async def pick_package(_):
        files = await ft.FilePicker().pick_files(allowed_extensions=["skill"])
        if not files:
            return
        pkg_path = Path(files[0].path)
        app._close_active_dialog()
        try:
            result = app.store.install_from_package(pkg_path)
            app._refresh_skills()
            app.show_snack(f"已安装 {result.name} v{result.version}")
            app._update_ui()
        except Exception as ex:
            app.show_snack(f"安装失败: {ex}", error=True)

    return ft.AlertDialog(
        title=ft.Text("安装 Skill"),
        content=ft.Column(
            spacing=16,
            tight=True,
            controls=[
                ft.Text("选择安装来源", size=13),
                ft.Row([
                    ft.FilledButton("从目录安装", icon=ft.Icons.FOLDER_OPEN, on_click=pick_directory),
                    ft.OutlinedButton("从 .skill 包安装", icon=ft.Icons.ARCHIVE, on_click=pick_package),
                ], spacing=12),
            ],
        ),
        actions=[
            ft.TextButton("取消", on_click=lambda _: app._close_active_dialog()),
        ],
    )


def build_uninstall_dialog(app, skill_name: str) -> ft.AlertDialog:
    def do_uninstall(_):
        app._close_active_dialog()
        try:
            app.store.uninstall(skill_name)
            app._refresh_skills()
            app.selected_skill_name = None
            app.show_snack(f"已卸载 {skill_name}")
            app._update_ui()
        except Exception as ex:
            app.show_snack(f"卸载失败: {ex}", error=True)

    return ft.AlertDialog(
        title=ft.Text("确认卸载"),
        content=ft.Text(f"确定要卸载 Skill「{skill_name}」吗？此操作不可撤销。"),
        actions=[
            ft.TextButton("取消", on_click=lambda _: app._close_active_dialog()),
            ft.TextButton("卸载", on_click=do_uninstall,
                          style=ft.ButtonStyle(color=ft.Colors.ERROR)),
        ],
    )
