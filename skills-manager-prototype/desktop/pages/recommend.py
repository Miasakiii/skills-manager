"""最近活动页面：展示最近使用和导出的 Skill。"""

from __future__ import annotations

import flet as ft

from ..components import FONT_TITLE, FONT_SUBTITLE, FONT_SECTION, FONT_CARD_NAME, FONT_CARD_DESC


def build_recommend_page(app) -> ft.Control:
    """构建最近活动页面。"""
    skills = app.skills

    if not skills:
        from ..components import EmptyState
        return EmptyState(
            on_install=lambda: app._show_install_dialog(),
            on_create=lambda: app.navigate("editor"),
        )

    recent_names = app.store.get_recent_skills(limit=10)
    export_history = app.store.get_export_history()

    recent_controls: list[ft.Control] = []
    if recent_names:
        for name in recent_names:
            skill_info = None
            for s in skills:
                if s.name == name:
                    skill_info = s
                    break
            if skill_info:
                recent_controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.HISTORY, size=20),
                        title=ft.Text(skill_info.name, size=FONT_CARD_NAME, weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(
                            skill_info.description or skill_info.summary or "",
                            size=FONT_CARD_DESC,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        on_click=lambda _, n=name: app.show_detail(n),
                    )
                )
    else:
        recent_controls.append(
            ft.Text("暂无使用记录", size=FONT_SUBTITLE, color=ft.Colors.ON_SURFACE_VARIANT)
        )

    export_controls: list[ft.Control] = []
    recent_exports = export_history[-10:] if export_history else []
    if recent_exports:
        for entry in reversed(recent_exports):
            export_controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.FILE_DOWNLOAD, size=20),
                    title=ft.Text(entry.get("skill_name", ""), size=FONT_CARD_NAME),
                    subtitle=ft.Text(
                        f"{entry.get('format', '')}  ·  {entry.get('output_path', '')}",
                        size=FONT_CARD_DESC,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
            )
    else:
        export_controls.append(
            ft.Text("暂无导出记录", size=FONT_SUBTITLE, color=ft.Colors.ON_SURFACE_VARIANT)
        )

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        expand=True,
        controls=[
            ft.Text("最近活动", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
            ft.Text("你最近使用和导出的 Skill", size=FONT_SUBTITLE),
            ft.Divider(),
            ft.Text("最近使用", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            ft.Card(content=ft.Column(spacing=0, controls=recent_controls)),
            ft.Divider(),
            ft.Text("最近导出", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            ft.Card(content=ft.Column(spacing=0, controls=export_controls)),
        ],
    )
