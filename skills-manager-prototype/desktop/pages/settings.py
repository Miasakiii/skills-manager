"""设置页：主题切换、默认格式、存储信息。"""

from __future__ import annotations

import flet as ft

from skills_manager.adapters import list_formats


def build_settings_page(app) -> ft.Control:
    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            ft.Text("设置", size=22, weight=ft.FontWeight.BOLD),
            ft.Divider(),

            ft.Text("主题", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Chip(
                    label=ft.Text("浅色"),
                    leading=ft.Icon(ft.Icons.LIGHT_MODE),
                    selected=app.theme_mode == ft.ThemeMode.LIGHT,
                    on_click=lambda _: _toggle_theme(app, ft.ThemeMode.LIGHT),
                ),
                ft.Chip(
                    label=ft.Text("深色"),
                    leading=ft.Icon(ft.Icons.DARK_MODE),
                    selected=app.theme_mode == ft.ThemeMode.DARK,
                    on_click=lambda _: _toggle_theme(app, ft.ThemeMode.DARK),
                ),
            ]),
            ft.Divider(),

            ft.Text("默认导出格式", size=16, weight=ft.FontWeight.BOLD),
            ft.Dropdown(
                options=[ft.DropdownOption(f) for f in list_formats()],
                value=app.export_format,
                width=200,
                on_select=lambda e: setattr(app, "export_format", e.control.value),
            ),
            ft.Divider(),

            ft.Text("存储信息", size=16, weight=ft.FontWeight.BOLD),
            ft.Text(f"存储路径: {app.store.base_dir}", size=12),
            ft.Text(f"已安装 Skill: {len(app.skills)} 个", size=12),
            ft.Text(f"支持格式: {', '.join(list_formats())}", size=12),
            ft.Divider(),

            ft.Row([
                ft.OutlinedButton("安装示例 Skills", icon=ft.Icons.DOWNLOAD, on_click=lambda _: _install_examples(app)),
            ]),
        ],
    )


def _toggle_theme(app, mode):
    app.theme_mode = mode
    app.page.theme_mode = mode
    app._update_ui()


def _install_examples(app):
    from pathlib import Path

    examples_dir = Path(__file__).parent.parent.parent / "examples"
    installed = []
    failed = []
    for example in sorted(examples_dir.iterdir()):
        if example.is_dir() and (example / "SKILL.md").exists():
            try:
                app.store.install(example, force=True)
                installed.append(example.name)
            except Exception:
                failed.append(example.name)
    app._refresh_skills()
    if installed:
        app.show_snack(f"已安装 {len(installed)} 个示例: {', '.join(installed)}")
    if failed:
        app.show_snack(f"安装失败: {', '.join(failed)}", error=True)
    app._update_ui()
