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
            ft.Divider(),

            ft.Text("同步到 Agent", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("安装时自动用 symlink 同步到各工具目录，Agent 立即可用", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Row([
                ft.FilledButton("重新同步全部", icon=ft.Icons.SYNC, on_click=lambda _: _resync_all(app)),
            ]),
            ft.Divider(),

            ft.Text("监视路径", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("自动扫描时会检查以下路径中的 Skill", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            *_build_watch_paths_section(app),
        ],
    )


def _build_watch_paths_section(app) -> list[ft.Control]:
    """构建监视路径管理区域。"""
    paths = app.store.get_watch_paths()
    controls: list[ft.Control] = []

    # 显示当前监视路径
    if paths:
        for p in list(paths):
            controls.append(ft.Row([
                ft.Text(p, size=12, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE,
                    tooltip="移除此路径",
                    data=p,
                    on_click=lambda e, app=app: _remove_watch_path(app, e.control.data),
                ),
            ]))
    else:
        controls.append(ft.Text("暂无自定义监视路径", size=12, italic=True, color=ft.Colors.ON_SURFACE_VARIANT))

    # 添加新路径
    path_input = ft.TextField(label="输入路径", expand=True, dense=True, text_size=12)

    def add_path(_):
        p = path_input.value.strip()
        if not p:
            return
        from pathlib import Path as P
        if not P(p).is_dir():
            app.show_snack(f"路径不存在: {p}", error=True)
            return
        app.store.add_watch_path(p)
        path_input.value = ""
        app._update_ui()

    controls.append(ft.Row([
        path_input,
        ft.IconButton(icon=ft.Icons.ADD, tooltip="添加监视路径", on_click=add_path),
    ]))

    return controls


def _remove_watch_path(app, path: str):
    app.store.remove_watch_path(path)
    app._update_ui()


def _toggle_theme(app, mode):
    app.theme_mode = mode
    app.page.theme_mode = mode
    app._update_ui()


def _resync_all(app):
    """重新同步全部已安装 Skill 到所有 Agent 目录。"""
    skills = app.store.list_all()
    if not skills:
        app.show_snack("没有已安装的 Skill，无需同步")
        return
    success = 0
    for s in skills:
        try:
            results = app.store.sync_skill_to_agents(s.name)
            if any(results.values()):
                success += 1
        except Exception:
            pass
    app.show_snack(f"已同步 {success}/{len(skills)} 个 Skill 到 Agent 目录")


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
