"""对话框：安装 Skill / 批量卸载 / 检查更新。"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from .components import FONT_BODY, FONT_SECTION, FONT_SMALL


def build_install_dialog(app) -> ft.AlertDialog:
    # URL 输入框
    url_input = ft.TextField(
        label="URL 地址",
        hint_text="https://github.com/user/repo 或 .skill 文件链接",
        expand=True,
    )

    async def pick_directory(_):
        path = await app.file_picker.get_directory_path()
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
        files = await app.file_picker.pick_files(allowed_extensions=["skill"])
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
        path = await app.file_picker.get_directory_path()
        if not path:
            return
        app._close_active_dialog()
        discovered = app.store.scan_directory(Path(path))
        if not discovered:
            app.show_snack(
                f"未在 {path} 中发现任何 Skill（需要包含 SKILL.md 的子目录）",
                error=True,
            )
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
                ft.Text("从本地安装", size=FONT_SECTION),
                ft.FilledButton(
                    "从目录安装", icon=ft.Icons.FOLDER_OPEN, on_click=pick_directory
                ),
                ft.OutlinedButton(
                    "从 .skill 包安装", icon=ft.Icons.ARCHIVE, on_click=pick_package
                ),
                ft.Divider(height=4),
                ft.Text("从 URL 安装", size=FONT_SECTION),
                url_input,
                ft.FilledButton(
                    "从 URL 安装", icon=ft.Icons.LANGUAGE, on_click=install_from_url
                ),
                ft.Divider(height=4),
                ft.Text("批量导入", size=FONT_SECTION),
                ft.FilledButton(
                    "自动扫描导入", icon=ft.Icons.FOLDER_SPECIAL, on_click=auto_scan
                ),
                ft.OutlinedButton(
                    "手动选择目录扫描",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=scan_directory,
                ),
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
            ft.TextButton(
                "卸载",
                on_click=do_uninstall,
                style=ft.ButtonStyle(color=ft.Colors.ERROR),
            ),
        ],
    )


def build_batch_uninstall_dialog(app, skill_names: list[str]) -> ft.AlertDialog:
    def do_batch_uninstall(_):
        app._close_active_dialog()
        success, failed = app.store.uninstall_many(list(skill_names))
        app._refresh_skills()
        app.checked_skills = set()
        app.batch_mode = False
        if success:
            app.show_snack(f"已卸载 {len(success)} 个 Skill")
        if failed:
            app.show_snack(f"{len(failed)} 个卸载失败", error=True)
        app._update_ui()

    return ft.AlertDialog(
        title=ft.Text("批量卸载"),
        content=ft.Column(
            spacing=8,
            tight=True,
            controls=[
                ft.Text(f"确定要卸载以下 {len(skill_names)} 个 Skill 吗？"),
                ft.Text(
                    "、".join(skill_names),
                    size=FONT_SMALL,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Text("此操作不可撤销。", color=ft.Colors.ERROR),
            ],
        ),
        actions=[
            ft.TextButton("取消", on_click=lambda _: app._close_active_dialog()),
            ft.TextButton(
                "卸载",
                on_click=do_batch_uninstall,
                style=ft.ButtonStyle(color=ft.Colors.ERROR),
            ),
        ],
    )


def build_check_updates_dialog(app) -> ft.AlertDialog:
    """显示可更新 Skill 列表，提供「一键更新」和单项更新。"""
    entries = app.store.check_outdated()
    updatable = [e for e in entries if e.get("updatable")]

    def update_one(name: str):
        try:
            app.store.update(name)
            app.show_snack(f"已更新 {name}")
        except Exception as ex:
            app.show_snack(f"{name} 更新失败：{ex}", error=True)
            return
        app._close_active_dialog()
        app._refresh_skills()
        app._update_ui()

    def update_all(_):
        app._close_active_dialog()
        success, failed = app.store.update_all()
        app._refresh_skills()
        if success:
            app.show_snack(f"已更新 {len(success)} 个 Skill")
        if failed:
            app.show_snack(f"{len(failed)} 个更新失败", error=True)
        app._update_ui()

    # 行列表
    rows: list[ft.Control] = []
    if not entries:
        rows.append(
            ft.Text(
                "尚未安装任何 Skill",
                size=FONT_BODY,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )
    else:
        for e in entries:
            cur = e.get("current_version") or "?"
            latest = e.get("latest_version")
            reason = e.get("reason", "")
            tag = (
                f"v{cur} → v{latest}"
                if latest and latest != cur
                else f"v{cur}"
            )
            if e.get("updatable"):
                if e.get("reason") == "remote":
                    label_color = ft.Colors.AMBER
                    badge = "远程"
                else:
                    label_color = ft.Colors.GREEN
                    badge = "可更新"
                action = ft.TextButton(
                    "更新",
                    on_click=lambda _, n=e["name"]: update_one(n),
                )
            else:
                label_color = ft.Colors.ON_SURFACE_VARIANT
                badge = "已最新" if reason == "已是最新" else "不可更新"
                action = ft.Container()
            rows.append(
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            content=ft.Text(badge, size=FONT_SMALL, color=ft.Colors.WHITE),
                            bgcolor=label_color,
                            padding=ft.Padding(8, 2, 8, 2),
                            border_radius=10,
                        ),
                        ft.Column(
                            spacing=2,
                            tight=True,
                            expand=True,
                            controls=[
                                ft.Text(
                                    e["name"],
                                    size=FONT_BODY,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"{tag}  ·  {reason}",
                                    size=FONT_SMALL,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                        ),
                        action,
                    ],
                )
            )

    actions: list[ft.Control] = [
        ft.TextButton("关闭", on_click=lambda _: app._close_active_dialog()),
    ]
    if updatable:
        actions.append(
            ft.FilledButton(
                f"一键更新 ({len(updatable)})",
                icon=ft.Icons.SYSTEM_UPDATE,
                on_click=update_all,
            )
        )

    return ft.AlertDialog(
        title=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.SYSTEM_UPDATE, color=ft.Colors.INDIGO),
                ft.Text(
                    "检查 Skill 更新", size=FONT_SECTION, weight=ft.FontWeight.BOLD
                ),
            ],
        ),
        content=ft.Container(
            width=520,
            content=ft.Column(
                tight=True,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text(
                        f"扫描结果：{len(entries)} 个 Skill，其中 {len(updatable)} 个可更新",
                        size=FONT_SMALL,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Divider(),
                    *rows,
                ],
            ),
        ),
        actions=actions,
    )
