"""可复用 UI 组件。"""

from __future__ import annotations

import flet as ft


class SkillCard(ft.Container):
    """Skill 卡片组件。"""

    CATEGORY_COLORS = {
        "language": ft.Colors.BLUE,
        "code": ft.Colors.GREEN,
        "data": ft.Colors.ORANGE,
        "research": ft.Colors.PURPLE,
        "writing": ft.Colors.TEAL,
        "automation": ft.Colors.RED,
        "misc": ft.Colors.GREY,
        "agent": ft.Colors.AMBER,
    }

    def __init__(self, skill_info, on_click, selected: bool = False):
        super().__init__()
        self.skill_info = skill_info
        tag_color = self.CATEGORY_COLORS.get(skill_info.category, ft.Colors.GREY)
        border = ft.border.all(2, tag_color) if selected else ft.border.all(1, ft.Colors.OUTLINE_VARIANT)

        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        self.border_radius = 12
        self.padding = 16
        self.ink = True
        self.border = border
        self.on_click = lambda _: on_click(skill_info.name)

        self.content = ft.Column(
            spacing=8,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.EXTENSION, color=tag_color, size=20),
                    ft.Text(skill_info.name, size=16, weight=ft.FontWeight.BOLD, color=tag_color),
                ]),
                ft.Text(
                    (skill_info.summary or skill_info.description or "")[:120],
                    size=12, color=ft.Colors.ON_SURFACE_VARIANT,
                    max_lines=4, overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Row([
                    ft.Chip(label=ft.Text(skill_info.version, size=11), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=0),
                    ft.Chip(label=ft.Text(skill_info.category or "misc", size=11), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=0),
                ], spacing=4),
            ],
        )


class SearchBar(ft.Container):
    """搜索栏组件。"""

    def __init__(self, on_search, placeholder: str = "搜索 Skill..."):
        super().__init__()
        self.on_search = on_search
        self.padding = ft.Padding(0, 0, 0, 12)

        self.content = ft.TextField(
            hint_text=placeholder,
            prefix_icon=ft.Icons.SEARCH,
            border=ft.InputBorder.OUTLINE,
            border_radius=8,
            on_change=lambda e: on_search(e.control.value),
        )


class EmptyState(ft.Container):
    """空状态占位组件。"""

    def __init__(self, on_install, on_create):
        super().__init__()
        self.expand = True
        self.alignment = ft.alignment.center
        self.content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.Icon(ft.Icons.INBOX_OUTLINED, size=64, color=ft.Colors.OUTLINE),
                ft.Text("还没有安装任何 Skill", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("安装示例 Skill 或创建新的 Skill 来开始使用", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row([
                    ft.FilledButton("安装 Skill", icon=ft.Icons.FILE_DOWNLOAD, on_click=lambda _: on_install()),
                    ft.OutlinedButton("新建 Skill", icon=ft.Icons.ADD, on_click=lambda _: on_create()),
                ], spacing=12),
            ],
        )
