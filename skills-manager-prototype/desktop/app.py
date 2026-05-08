"""Skills Manager 桌面应用 — 主控逻辑。"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from skills_manager.store import Store


class App:
    """应用主控类：管理全局状态、导航、布局。"""

    def __init__(self):
        self.store = Store()
        self.skills: list = []
        self.selected_skill_name: str | None = None
        self.current_page = "browse"
        self.export_format = "openai"
        self.theme_mode = ft.ThemeMode.LIGHT

        # 对话框引用
        self._active_dialog: ft.AlertDialog | None = None

        # UI 组件引用（build 后赋值）
        self.page: ft.Page | None = None
        self.sidebar: ft.Container | None = None
        self.content_area: ft.Container | None = None

    def build(self, page: ft.Page):
        self.page = page
        page.title = "Skills Manager"
        page.window.width = 1100
        page.window.height = 700
        page.theme_mode = self.theme_mode
        page.padding = 0
        page.fonts = {"monospace": "Cascadia Code, Consolas, monospace"}

        self._refresh_skills()

        self.sidebar = self._build_sidebar()
        self.content_area = ft.Container(expand=True, padding=24, content=self._build_current_page())

        page.add(ft.Row([self.sidebar, ft.VerticalDivider(width=1), self.content_area], expand=True))

    # ── 数据 ──────────────────────────────────────────────────

    def _refresh_skills(self):
        try:
            self.skills = self.store.list_all()
        except Exception as e:
            self.skills = []
            self.show_snack(f"加载 Skill 列表失败: {e}", error=True)

    # ── 导航 ──────────────────────────────────────────────────

    def navigate(self, page_id: str):
        self.current_page = page_id
        self.selected_skill_name = None
        self._update_ui()

    def show_detail(self, skill_name: str):
        self.selected_skill_name = skill_name
        self._update_ui()

    def go_back(self):
        self.selected_skill_name = None
        self._update_ui()

    def _update_ui(self):
        # 替换 sidebar 的 content（而非 sidebar 本身），确保页面树中的旧 Container 被更新
        new_sidebar = self._build_sidebar()
        self.sidebar.content = new_sidebar.content
        self.content_area.content = self._build_current_page()
        self.page.update()

    # ── 页面构建（委托给各模块）──────────────────────────────

    def _build_current_page(self) -> ft.Control:
        from .pages.browse import build_browse_page
        from .pages.detail import build_detail_page
        from .pages.export import build_export_page
        from .pages.editor import build_editor_page
        from .pages.settings import build_settings_page

        if self.selected_skill_name:
            return build_detail_page(self)
        if self.current_page == "browse":
            return build_browse_page(self)
        if self.current_page == "export":
            return build_export_page(self)
        if self.current_page == "editor":
            return build_editor_page(self)
        if self.current_page == "settings":
            return build_settings_page(self)
        return build_browse_page(self)

    # ── 侧边栏 ────────────────────────────────────────────────

    def _build_sidebar(self) -> ft.Container:
        nav_items = [
            ("browse", ft.Icons.GRID_VIEW, "浏览"),
            ("export", ft.Icons.FILE_DOWNLOAD, "批量导出"),
            ("editor", ft.Icons.EDIT, "编辑器"),
            ("settings", ft.Icons.SETTINGS, "设置"),
        ]

        nav_buttons = []
        for page_id, icon, label in nav_items:
            is_active = self.current_page == page_id
            nav_buttons.append(ft.Container(
                content=ft.Row([ft.Icon(icon, size=18), ft.Text(label, size=13)], spacing=10),
                bgcolor=ft.Colors.SECONDARY_CONTAINER if is_active else ft.Colors.TRANSPARENT,
                border_radius=8,
                padding=ft.Padding(12, 8, 12, 8),
                ink=True,
                on_click=lambda _, pid=page_id: self.navigate(pid),
            ))

        return ft.Container(
            width=180,
            padding=ft.Padding(12, 16, 12, 16),
            bgcolor=ft.Colors.SURFACE,
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text("Skills Manager", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"v0.1.0  ·  {len(self.skills)} 个 Skill", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Divider(height=20),
                    ft.TextButton(
                        content=ft.Row([ft.Icon(ft.Icons.ADD, size=18), ft.Text("安装 Skill", size=13)], spacing=10),
                        on_click=lambda _: self._show_install_dialog(),
                    ),
                    ft.Divider(height=8),
                ] + nav_buttons,
            ),
        )

    # ── 安装对话框 ────────────────────────────────────────────

    def _show_install_dialog(self):
        from .dialogs import build_install_dialog
        self._active_dialog = build_install_dialog(self)
        self.page.show_dialog(self._active_dialog)

    def _close_active_dialog(self):
        if self._active_dialog:
            self._active_dialog.open = False
            self.page.update()
            self._active_dialog = None

    # ── 通用工具 ──────────────────────────────────────────────

    def show_snack(self, text: str, error: bool = False):
        snack = ft.SnackBar(
            content=ft.Text(text),
            bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
            duration=3000,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def copy_to_clipboard(self, content: str):
        # Flet 0.84 desktop 不支持 set_clipboard，显示对话框让用户手动复制
        dialog = ft.AlertDialog(
            title=ft.Text("导出结果"),
            content=ft.Container(
                content=ft.Text(content, font_family="monospace", size=12),
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                border_radius=8,
                padding=16,
                width=500,
                height=300,
            ),
            actions=[ft.TextButton("关闭", on_click=lambda e: self._close_active_dialog())],
        )
        self._active_dialog = dialog
        self.page.show_dialog(dialog)
