"""Skills Manager — Flet 原型验证

验证 Flet 桌面框架的可行性：
1. 侧边栏导航 + 内容区布局
2. Skill 卡片网格展示
3. Skill 详情面板
4. 导出预览
"""

from __future__ import annotations

import json
from pathlib import Path

import flet as ft

from skills_manager.adapters import get_adapter, list_formats
from skills_manager.parser import parse_skill_md
from skills_manager.store import Store


class SkillCard(ft.Container):
    """Skill 卡片组件。"""

    def __init__(self, skill_info, on_click):
        super().__init__()
        self.skill_info = skill_info
        self.on_click = on_click
        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        self.border_radius = 12
        self.padding = 16
        self.ink = True
        self.on_click = lambda _: on_click(skill_info.name)

        category_colors = {
            "language": ft.Colors.BLUE,
            "code": ft.Colors.GREEN,
            "data": ft.Colors.ORANGE,
            "research": ft.Colors.PURPLE,
            "writing": ft.Colors.TEAL,
            "automation": ft.Colors.RED,
            "misc": ft.Colors.GREY,
            "agent": ft.Colors.AMBER,
        }
        tag_color = category_colors.get(skill_info.category, ft.Colors.GREY)

        self.content = ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    [
                        ft.Icon(ft.Icons.EXTENSION, color=tag_color, size=20),
                        ft.Text(
                            skill_info.name,
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=tag_color,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Text(
                    (skill_info.summary or skill_info.description or "")[:80],
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    max_lines=3,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Row(
                    [
                        ft.Chip(
                            label=ft.Text(skill_info.version, size=11),
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                            padding=0,
                        ),
                    ]
                    + (
                        [
                            ft.Chip(
                                label=ft.Text(skill_info.category or "misc", size=11),
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                padding=0,
                            )
                        ]
                        if skill_info.category
                        else []
                    ),
                    spacing=4,
                ),
            ],
        )


class PrototypeApp:
    """原型应用。"""

    def __init__(self):
        self.store = Store()
        self.skills: list = []
        self.selected_skill_name: str | None = None
        self.current_page = "browse"
        self.export_format = "openai"

    def build(self, page: ft.Page):
        page.title = "Skills Manager — 原型"
        page.window.width = 1100
        page.window.height = 700
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 0
        page.fonts = {"monospace": "Cascadia Code, Consolas, monospace"}

        self.page = page

        # 加载数据
        self._refresh_skills()

        # 布局
        self.sidebar = self._build_sidebar()
        self.content_area = ft.Container(
            expand=True,
            padding=24,
            content=self._build_browse_page(),
        )

        page.add(
            ft.Row(
                [self.sidebar, ft.VerticalDivider(width=1), self.content_area],
                expand=True,
            )
        )

    def _refresh_skills(self):
        self.skills = self.store.list_all()

    def _build_sidebar(self) -> ft.Container:
        nav_items = [
            ("browse", ft.Icons.GRID_VIEW, "浏览"),
            ("export", ft.Icons.FILE_DOWNLOAD, "导出"),
            ("editor", ft.Icons.EDIT, "编辑器"),
            ("settings", ft.Icons.SETTINGS, "设置"),
        ]

        nav_buttons = []
        for page_id, icon, label in nav_items:
            is_active = self.current_page == page_id
            btn = ft.TextButton(
                content=ft.Row(
                    [
                        ft.Icon(icon, size=18, color=ft.Colors.ON_SURFACE),
                        ft.Text(label, size=13),
                    ],
                    spacing=10,
                ),
                style=ft.ButtonStyle(
                    bgcolor=(
                        ft.Colors.SECONDARY_CONTAINER
                        if is_active
                        else ft.Colors.TRANSPARENT
                    ),
                ),
                on_click=lambda _, pid=page_id: self._navigate(pid),
            )
            nav_buttons.append(btn)

        return ft.Container(
            width=180,
            padding=ft.Padding(12, 16, 12, 16),
            bgcolor=ft.Colors.SURFACE,
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text("Skills Manager", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text("原型验证", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Divider(height=20),
                ]
                + nav_buttons,
            ),
        )

    def _navigate(self, page_id: str):
        self.current_page = page_id
        self.sidebar = self._build_sidebar()
        if page_id == "browse":
            self.content_area.content = self._build_browse_page()
        elif page_id == "export":
            self.content_area.content = self._build_export_page()
        elif page_id == "editor":
            self.content_area.content = self._build_editor_page()
        elif page_id == "settings":
            self.content_area.content = self._build_settings_page()
        self.page.update()

    # ── 浏览页 ──────────────────────────────────────────────

    def _build_browse_page(self) -> ft.Control:
        if self.selected_skill_name:
            return self._build_detail_view()

        cards = []
        for s in self.skills:
            cards.append(SkillCard(s, on_click=self._show_detail))

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            controls=[
                ft.Row(
                    [
                        ft.Text("Skill 库", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"{len(self.skills)} 个已安装",
                            size=13,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Column(col={"sm": 12, "md": 6, "lg": 4}, controls=[card])
                        for card in cards
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
            ],
        )

    def _show_detail(self, skill_name: str):
        self.selected_skill_name = skill_name
        self.content_area.content = self._build_browse_page()
        self.page.update()

    def _build_detail_view(self) -> ft.Control:
        try:
            ir = self.store.get_skill_ir(self.selected_skill_name)
        except Exception:
            self.selected_skill_name = None
            return self._build_browse_page()

        # 参数表
        param_rows = []
        for p in ir.parameters:
            param_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(p.name, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(p.type)),
                        ft.DataCell(
                            ft.Icon(
                                ft.Icons.CHECK if p.required else ft.Icons.CLOSE,
                                size=16,
                                color=(
                                    ft.Colors.GREEN
                                    if p.required
                                    else ft.Colors.GREY
                                ),
                            )
                        ),
                        ft.DataCell(ft.Text(p.description, size=12)),
                    ]
                )
            )

        param_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("参数")),
                ft.DataColumn(ft.Text("类型")),
                ft.DataColumn(ft.Text("必需")),
                ft.DataColumn(ft.Text("说明")),
            ],
            rows=param_rows,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            ),
        )

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            controls=[
                ft.Row(
                    [
                        ft.TextButton(
                            "← 返回",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda _: self._go_back(),
                        ),
                    ]
                ),
                ft.Row(
                    [
                        ft.Column(
                            spacing=8,
                            controls=[
                                ft.Text(
                                    ir.name,
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"v{ir.version}  ·  {ir.category or '未分类'}",
                                    size=13,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            expand=True,
                        ),
                        ft.FilledButton(
                            "导出此 Skill",
                            icon=ft.Icons.FILE_DOWNLOAD,
                            on_click=lambda _: self._quick_export(ir),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(ir.description, size=15, italic=True),
                ft.Divider(),
                ft.Text("参数定义", size=16, weight=ft.FontWeight.BOLD),
                param_table if ir.parameters else ft.Text("无参数"),
                ft.Divider(),
                ft.Text("导出预览", size=16, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.Dropdown(
                            options=[
                                ft.DropdownOption(fmt) for fmt in list_formats()
                            ],
                            value=self.export_format,
                            on_change=lambda e: self._switch_export_format(e),
                            width=150,
                        ),
                    ]
                ),
                ft.Container(
                    content=ft.Text(
                        self._generate_preview(ir),
                        font_family="monospace",
                        size=12,
                    ),
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=8,
                    padding=16,
                ),
            ],
        )

    def _go_back(self):
        self.selected_skill_name = None
        self.content_area.content = self._build_browse_page()
        self.page.update()

    def _switch_export_format(self, event):
        self.export_format = event.control.value
        # 触发显示更新
        self.content_area.content = self._build_browse_page()
        self.page.update()

    def _generate_preview(self, ir) -> str:
        try:
            adapter = get_adapter(self.export_format)
            return adapter.export(ir)
        except Exception as e:
            return f"Error: {e}"

    def _quick_export(self, ir):
        """将当前格式的导出结果复制到剪贴板。"""
        content = self._generate_preview(ir)
        self.page.set_clipboard(content)
        self.page.show_snack_bar(
            ft.SnackBar(
                ft.Text(f"已复制 {self.export_format} 格式到剪贴板"),
                action="OK",
            )
        )

    # ── 导出页 ──────────────────────────────────────────────

    def _build_export_page(self) -> ft.Control:
        skill_checkboxes = []
        for s in self.skills:
            skill_checkboxes.append(
                ft.Checkbox(
                    label=f"{s.name} v{s.version}",
                    value=False,
                )
            )

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            controls=[
                ft.Text("批量导出", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("选择要导出的 Skills 和目标格式", size=13),
                ft.Divider(),
                ft.Text("选择 Skills", size=16, weight=ft.FontWeight.BOLD),
                ft.Column(controls=skill_checkboxes, spacing=4),
                ft.Divider(),
                ft.Text("目标格式", size=16, weight=ft.FontWeight.BOLD),
                ft.Dropdown(
                    options=[ft.DropdownOption(fmt) for fmt in list_formats()],
                    value="openai",
                    width=200,
                ),
                ft.FilledButton(
                    "导出选中",
                    icon=ft.Icons.FILE_DOWNLOAD,
                    on_click=lambda _: self.page.show_snack_bar(
                        ft.SnackBar(ft.Text("原型：导出功能模拟"))
                    ),
                ),
            ],
        )

    # ── 编辑器页（占位）─────────────────────────────────────

    def _build_editor_page(self) -> ft.Control:
        return ft.Column(
            spacing=16,
            controls=[
                ft.Text("Skill 编辑器", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("（原型占位 — 完整编辑器在 Phase 3 实现）", size=13),
                ft.Divider(),
                ft.TextField(
                    multiline=True,
                    min_lines=15,
                    max_lines=30,
                    hint_text="在此编写 SKILL.md...",
                    border=ft.InputBorder.OUTLINE,
                ),
                ft.Row(
                    [
                        ft.FilledButton("保存", icon=ft.Icons.SAVE),
                        ft.OutlinedButton("预览 IR", icon=ft.Icons.PREVIEW),
                    ],
                    spacing=8,
                ),
            ],
        )

    # ── 设置页（占位）───────────────────────────────────────

    def _build_settings_page(self) -> ft.Control:
        return ft.Column(
            spacing=16,
            controls=[
                ft.Text("设置", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("（原型占位 — 完整设置在 Phase 3 实现）", size=13),
                ft.Divider(),
                ft.Text("主题", size=16),
                ft.Row(
                    [
                        ft.Chip(
                            label=ft.Text("浅色"),
                            leading=ft.Icon(ft.Icons.LIGHT_MODE),
                            selected=True,
                        ),
                        ft.Chip(
                            label=ft.Text("深色"),
                            leading=ft.Icon(ft.Icons.DARK_MODE),
                        ),
                    ]
                ),
                ft.Divider(),
                ft.Text("默认导出格式", size=16),
                ft.Dropdown(
                    options=[ft.DropdownOption(fmt) for fmt in list_formats()],
                    value="openai",
                    width=200,
                ),
                ft.Divider(),
                ft.Text(f"存储路径: {self.store.base_dir}", size=12),
            ],
        )


def main(page: ft.Page):
    app = PrototypeApp()
    app.build(page)


if __name__ == "__main__":
    ft.run(main)
