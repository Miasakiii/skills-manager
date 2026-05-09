"""对话框：安装 Skill。"""

from __future__ import annotations

from pathlib import Path

import flet as ft


def build_install_dialog(app) -> ft.AlertDialog:
    # URL 输入框
    url_input = ft.TextField(
        label="URL 地址",
        hint_text="https://github.com/user/repo 或 .skill 文件链接",
        expand=True,
    )

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

    async def install_from_url(_):
        url = url_input.value.strip()
        if not url:
            app.show_snack("请输入 URL", error=True)
            return
        app._close_active_dialog()
        try:
            result = app.store.install_from_url(url)
            app._refresh_skills()
            app.show_snack(f"已安装 {result.name} v{result.version}")
            app._update_ui()
        except Exception as ex:
            app.show_snack(f"安装失败: {ex}", error=True)

    async def auto_scan(_):
        app._close_active_dialog()
        installed, failed = app.auto_discover_and_install()
        app._refresh_skills()
        if not installed and not failed:
            app.show_snack("未发现新的 Skill（预设路径中无可安装的 Skill）")
            return
        msg = f"已导入 {len(installed)} 个 Skill"
        if failed:
            msg += f"，{len(failed)} 个失败"
        app.show_snack(msg, error=bool(failed))
        app._update_ui()

    async def scan_directory(_):
        path = await ft.FilePicker().get_directory_path()
        if not path:
            return
        app._close_active_dialog()
        discovered = app.store.scan_directory(Path(path))
        if not discovered:
            app.show_snack(f"未在 {path} 中发现任何 Skill（需要包含 SKILL.md 的子目录）", error=True)
            return
        installed, failed = app.store.scan_and_install(Path(path))
        app._refresh_skills()
        msg = f"已导入 {len(installed)} 个 Skill"
        if failed:
            msg += f"，{len(failed)} 个失败"
        app.show_snack(msg, error=bool(failed))
        app._update_ui()

    return ft.AlertDialog(
        title=ft.Text("安装 Skill"),
        content=ft.Column(
            spacing=12,
            tight=True,
            controls=[
                ft.Text("从本地安装", size=13),
                ft.FilledButton("从目录安装", icon=ft.Icons.FOLDER_OPEN, on_click=pick_directory),
                ft.OutlinedButton("从 .skill 包安装", icon=ft.Icons.ARCHIVE, on_click=pick_package),
                ft.Divider(height=4),
                ft.Text("从 URL 安装", size=13),
                url_input,
                ft.FilledButton("从 URL 安装", icon=ft.Icons.LANGUAGE, on_click=install_from_url),
                ft.Divider(height=4),
                ft.Text("批量导入", size=13),
                ft.FilledButton("自动扫描导入", icon=ft.Icons.FOLDER_SPECIAL, on_click=auto_scan),
                ft.OutlinedButton("手动选择目录扫描", icon=ft.Icons.FOLDER_OPEN, on_click=scan_directory),
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
