"""Skills Manager 桌面应用 — 主控逻辑。"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from skills_manager import __version__
from skills_manager.logging import get_logger
from skills_manager.store import Store

from .components import FONT_SECTION, FONT_BODY, FONT_SMALL

logger = get_logger(__name__)


class App:
    """应用主控类：管理全局状态、导航、布局。"""

    def __init__(self):
        self.store = Store()
        self.skills: list = []
        self.selected_skill_name: str | None = None
        self.current_page = "browse"
        self.export_format = "openai"
        self.theme_mode = ft.ThemeMode.LIGHT
        self.compact_mode = True  # 简洁/详细模式
        self._health_cache: tuple | None = None  # (errors, warnings) 缓存

        # 对话框引用
        self._active_dialog: ft.AlertDialog | None = None

        # FilePicker（在 build 时创建并 attach 到 page.services，确保有 parent）
        self.file_picker: ft.FilePicker | None = None

        # UI 组件引用（build 后赋值）
        self.page: ft.Page | None = None
        self.sidebar: ft.Container | None = None
        self.content_area: ft.Container | None = None

        # ── 浏览页状态 ──
        self.search_query: str = ""
        self.selected_skill_type: str = ""
        self.selected_category: str = ""
        self.selected_tag: str = ""
        self.sort_by: str = "name_asc"
        self.view_mode: str = "grid"
        self.batch_mode: bool = False
        self.checked_skills: set[str] = set()
        self.batch_export_skills: list[str] = []

        # ── 导出页状态 ──
        self._export_selected: dict[str, bool] = {}
        self._batch_export_format: str = "openai"
        self._batch_pack_format: str = ""
        self._batch_output_dir: str = ""

        # ── 导入页状态 ──
        self._import_scan_path: str = ""
        self._import_results: list[dict] = []
        self._import_selected: dict[str, bool] = {}

        # ── 编辑器页状态 ──
        self._new_skill_name: str = ""
        self._new_skill_version: str = "1.0.0"
        self._new_skill_description: str = ""
        self._new_skill_category: str = "misc"
        self._new_skill_tags: str = ""
        self._new_skill_type: str = "component"
        self._new_skill_intent: str = ""
        self._preview_format: str = "markdown"
        self._generated_content: str = ""

        # ── MCP 配置页状态 ──
        from pathlib import Path as _Path

        self.mcp_manager = None  # 懒加载，避免桌面端启动时 import 失败
        self.mcp_selected_profile: str = ""
        self.mcp_custom_paths: dict[str, _Path] = {}

    def build(self, page: ft.Page):
        self.page = page
        page.title = "Skills Manager"
        page.window.width = 1200
        page.window.height = 760
        page.window.min_width = 800
        page.window.min_height = 500
        page.theme_mode = self.theme_mode
        page.padding = 0
        page.fonts = {"monospace": "Cascadia Code, Consolas, monospace"}

        # 全局字体栈：优先使用系统 UI 字体，中文回退微软雅黑
        _font_family = "Segoe UI, Microsoft YaHei UI, PingFang SC, Noto Sans SC, system-ui, sans-serif"

        # 自定义主题配色（靛蓝主色 + 珊瑚点缀）
        page.theme = ft.Theme(
            font_family=_font_family,
            color_scheme=ft.ColorScheme(
                primary=ft.Colors.INDIGO,
                on_primary=ft.Colors.WHITE,
                primary_container=ft.Colors.INDIGO_50,
                on_primary_container=ft.Colors.INDIGO_900,
                secondary=ft.Colors.DEEP_PURPLE,
                on_secondary=ft.Colors.WHITE,
                secondary_container=ft.Colors.DEEP_PURPLE_50,
                on_secondary_container=ft.Colors.DEEP_PURPLE_900,
                surface=ft.Colors.WHITE,
                surface_container=ft.Colors.GREY_50,
                surface_container_highest=ft.Colors.GREY_100,
                on_surface=ft.Colors.GREY_900,
                on_surface_variant=ft.Colors.GREY_600,
                outline=ft.Colors.GREY_300,
                outline_variant=ft.Colors.GREY_200,
                error=ft.Colors.RED_600,
                on_error=ft.Colors.WHITE,
                error_container=ft.Colors.RED_50,
                on_error_container=ft.Colors.RED_900,
            ),
        )
        page.dark_theme = ft.Theme(
            font_family=_font_family,
            color_scheme=ft.ColorScheme(
                primary=ft.Colors.INDIGO_300,
                on_primary=ft.Colors.INDIGO_900,
                primary_container=ft.Colors.INDIGO_700,
                on_primary_container=ft.Colors.INDIGO_50,
                secondary=ft.Colors.DEEP_PURPLE_300,
                on_secondary=ft.Colors.DEEP_PURPLE_900,
                secondary_container=ft.Colors.DEEP_PURPLE_700,
                on_secondary_container=ft.Colors.DEEP_PURPLE_50,
                surface=ft.Colors.GREY_900,
                surface_container=ft.Colors.GREY_800,
                surface_container_highest=ft.Colors.GREY_700,
                on_surface=ft.Colors.GREY_100,
                on_surface_variant=ft.Colors.GREY_400,
                outline=ft.Colors.GREY_600,
                outline_variant=ft.Colors.GREY_700,
                error=ft.Colors.RED_300,
                on_error=ft.Colors.RED_900,
                error_container=ft.Colors.RED_900,
                on_error_container=ft.Colors.RED_100,
            ),
        )

        self._refresh_skills()

        # 首次启动无 Skill 时自动导入示例
        if not self.skills:
            self._auto_import_examples()

        # 后台自动分类（对未分类的 skill 运行关键词推断）
        uncategorized = sum(1 for s in self.skills if not getattr(s, "category", None))
        if uncategorized > 0:
            import threading

            def _auto_classify():
                try:
                    changed = self.store.reclassify_all()
                    if changed > 0:
                        self._refresh_skills()
                except Exception:
                    logger.exception("Background auto-classification failed")

            threading.Thread(target=_auto_classify, daemon=True).start()

        # 后台检查更新
        self._check_for_updates()

        self.sidebar = self._build_sidebar()
        self.content_area = ft.Container(
            expand=True, padding=24, content=self._build_current_page()
        )

        # 注册全局快捷键
        page.on_keyboard_event = self._on_keyboard

        page.add(
            ft.Row(
                [self.sidebar, ft.VerticalDivider(width=1), self.content_area],
                expand=True,
            )
        )

        # Flet 0.85+: FilePicker 是 Service，必须通过 page.services setter 注册
        # （直接 append 不会触发 parent 绑定）。在 page.add 之后做，确保 root view
        # 已初始化。
        self.file_picker = ft.FilePicker()
        page.services = list(page.services) + [self.file_picker]
        page.update()

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
        self._update_content()
        self._update_sidebar_state()

    def show_detail(self, skill_name: str):
        self.selected_skill_name = skill_name
        self._update_content()

    def go_back(self):
        self.selected_skill_name = None
        self._update_content()

    def _update_ui(self):
        """全量更新：侧边栏 + 内容区。仅在数据变化（安装/卸载/翻译）时调用。"""
        new_sidebar = self._build_sidebar()
        self.sidebar.content = new_sidebar.content
        self.content_area.content = self._build_current_page()
        self.page.update()

    def _update_content(self):
        """仅刷新内容区，保留侧边栏。导航/详情切换时使用。"""
        self.content_area.content = self._build_current_page()
        self.page.update()

    def _update_sidebar_state(self):
        """仅刷新侧边栏。导航切换时使用，避免重建内容区。"""
        new_sidebar = self._build_sidebar()
        self.sidebar.content = new_sidebar.content
        self.page.update()

    # ── 页面构建（委托给各模块）──────────────────────────────

    def _build_current_page(self) -> ft.Control:
        from .pages.browse import build_browse_page
        from .pages.detail import build_detail_page
        from .pages.export import build_export_page
        from .pages.editor import build_editor_page
        from .pages.settings import build_settings_page
        from .pages.import_page import build_import_page
        from .pages.recommend import build_recommend_page
        from .pages.mcp import build_mcp_page

        if self.selected_skill_name:
            return build_detail_page(self)
        if self.current_page == "browse":
            return build_browse_page(self)
        if self.current_page == "export":
            return build_export_page(self)
        if self.current_page == "import":
            return build_import_page(self)
        if self.current_page == "recommend":
            return build_recommend_page(self)
        if self.current_page == "editor":
            return build_editor_page(self)
        if self.current_page == "mcp":
            return build_mcp_page(self)
        if self.current_page == "settings":
            return build_settings_page(self)
        return build_browse_page(self)

    # ── 侧边栏 ────────────────────────────────────────────────

    def _build_sidebar(self) -> ft.Container:
        nav_items = [
            ("browse", ft.Icons.GRID_VIEW, "浏览"),
            ("export", ft.Icons.FILE_DOWNLOAD, "批量导出"),
            ("import", ft.Icons.FILE_UPLOAD, "批量导入"),
            ("recommend", ft.Icons.HISTORY, "最近"),
            ("editor", ft.Icons.EDIT, "编辑器"),
            ("mcp", ft.Icons.HUB, "MCP 配置"),
            ("settings", ft.Icons.SETTINGS, "设置"),
        ]

        nav_buttons = []
        for page_id, icon, label in nav_items:
            is_active = self.current_page == page_id
            nav_buttons.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(
                                    icon,
                                    size=18,
                                    color=ft.Colors.WHITE
                                    if is_active
                                    else ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                bgcolor=ft.Colors.INDIGO
                                if is_active
                                else ft.Colors.TRANSPARENT,
                                border_radius=6,
                                padding=ft.Padding(4, 4, 4, 4),
                            ),
                            ft.Text(
                                label,
                                size=FONT_BODY,
                                weight=ft.FontWeight.BOLD
                                if is_active
                                else ft.FontWeight.W_500,
                                color=ft.Colors.INDIGO
                                if is_active
                                else ft.Colors.ON_SURFACE,
                            ),
                        ],
                        spacing=10,
                    ),
                    bgcolor=ft.Colors.INDIGO_50 if is_active else ft.Colors.TRANSPARENT,
                    border_radius=10,
                    padding=ft.Padding(10, 8, 12, 8),
                    border=ft.Border(
                        left=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                        top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                        right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                        bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                    ),
                    animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
                    ink=True,
                    on_click=lambda _, pid=page_id: self.navigate(pid),
                )
            )

        return ft.Container(
            width=180,
            padding=ft.Padding(0, 0, 0, 0),
            bgcolor=ft.Colors.SURFACE,
            content=ft.Column(
                spacing=0,
                controls=[
                    # 头部区域
                    ft.Container(
                        padding=ft.Padding(16, 20, 16, 12),
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Row(
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Container(
                                            content=ft.Icon(
                                                ft.Icons.MEMORY,
                                                color=ft.Colors.WHITE,
                                                size=22,
                                            ),
                                            bgcolor=ft.Colors.INDIGO,
                                            border_radius=10,
                                            padding=ft.Padding(8, 8, 8, 8),
                                            shadow=ft.BoxShadow(
                                                spread_radius=0,
                                                blur_radius=8,
                                                color=ft.Colors.with_opacity(
                                                    0.3, ft.Colors.INDIGO
                                                ),
                                                offset=ft.Offset(0, 2),
                                            ),
                                        ),
                                        ft.Column(
                                            spacing=2,
                                            controls=[
                                                ft.Text(
                                                    "Skills Manager",
                                                    size=FONT_SECTION,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                ft.Text(
                                                    f"v{__version__}",
                                                    size=FONT_SMALL,
                                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        spacing=6,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Container(
                                                width=6,
                                                height=6,
                                                bgcolor=ft.Colors.GREEN,
                                                border_radius=3,
                                            ),
                                            ft.Text(
                                                f"{len(self.skills)} 个 Skill 已就绪",
                                                size=FONT_SMALL,
                                                color=ft.Colors.ON_SURFACE_VARIANT,
                                            ),
                                        ],
                                    ),
                                    padding=ft.Padding(8, 4, 8, 4),
                                    border_radius=6,
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                ),
                            ],
                        ),
                    ),
                    ft.Divider(height=1),
                    # 安装按钮
                    ft.Container(
                        padding=ft.Padding(8, 8, 8, 4),
                        content=ft.FilledButton(
                            content=ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.ADD_CIRCLE_OUTLINE,
                                        size=18,
                                        color=ft.Colors.WHITE,
                                    ),
                                    ft.Text(
                                        "安装 Skill",
                                        size=FONT_BODY,
                                        color=ft.Colors.WHITE,
                                    ),
                                ],
                                spacing=10,
                            ),
                            on_click=lambda _: self._show_install_dialog(),
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.INDIGO,
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.Padding(14, 10, 14, 10),
                                elevation=2,
                                shadow_color=ft.Colors.with_opacity(
                                    0.2, ft.Colors.INDIGO
                                ),
                            ),
                        ),
                    ),
                    ft.Divider(height=1),
                    # 导航区域
                    ft.Container(
                        padding=ft.Padding(8, 8, 8, 8),
                        expand=True,
                        content=ft.Column(
                            spacing=4,
                            controls=nav_buttons,
                        ),
                    ),
                    # 健康检查
                    ft.Container(
                        padding=ft.Padding(8, 0, 8, 4),
                        content=ft.Container(
                            content=ft.TextButton(
                                content=ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.HEALTH_AND_SAFETY,
                                            size=16,
                                            color=self._health_status_color(),
                                        ),
                                        ft.Text(
                                            self._health_status_text(), size=FONT_SMALL
                                        ),
                                    ],
                                    spacing=8,
                                ),
                                on_click=lambda _: self._show_health_dialog(),
                            ),
                            border_radius=8,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        ),
                    ),
                    # 底部版本信息
                    ft.Container(
                        padding=ft.Padding(12, 10, 12, 10),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        border=ft.Border(
                            top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                            left=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                            right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                            bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                        ),
                        content=ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(
                                    ft.Icons.ROCKET_LAUNCH_OUTLINED,
                                    size=14,
                                    color=ft.Colors.INDIGO,
                                ),
                                ft.Text(
                                    "Skills Manager",
                                    size=FONT_SMALL,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        f"v{__version__}",
                                        size=FONT_SMALL,
                                        color=ft.Colors.INDIGO,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    bgcolor=ft.Colors.INDIGO_50,
                                    border_radius=6,
                                    padding=ft.Padding(6, 3, 6, 3),
                                    ink=True,
                                    on_click=lambda _: self._show_update_dialog(),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

    # ── 自动发现 ──────────────────────────────────────────

    def _get_scan_paths(self) -> list[Path]:
        """返回自动扫描的预设路径列表（完全兼容 cc-switch 生态）。"""
        home = Path.home()
        paths: list[Path] = [
            # 自身 store
            self.store.store_dir,
            # cc-switch SSOT 主存储（用户 200+ skill 在这里）
            home / ".cc-switch" / "skills",
            # 各 CLI 工具 skills 目录
            home / ".claude" / "skills",
            home / ".codex" / "skills",
            home / ".gemini" / "skills",
            home / ".config" / "opencode" / "skills",
            home / ".openclaw" / "skills",
            home / ".agents" / "skills",
        ]
        # 项目内置示例
        examples_dir = Path(__file__).parent.parent / "examples"
        if examples_dir.is_dir():
            paths.append(examples_dir)
        # Claude Desktop 可能有独立目录
        claude_desktop = home / ".claude-desktop" / "skills"
        if claude_desktop.is_dir():
            paths.append(claude_desktop)
        # 用户自定义监视路径
        for p in self.store.get_watch_paths():
            paths.append(Path(p))
        return paths

    def auto_discover(self) -> list[Path]:
        """自动扫描预设路径，返回发现但未安装的 Skill 目录列表。"""
        return self.store.discover_in_paths(self._get_scan_paths())

    def auto_discover_and_install(self) -> tuple[list[str], list[tuple[str, str]]]:
        """自动发现并安装全部未安装的 Skill。"""
        discovered = self.auto_discover()
        if not discovered:
            return [], []
        installed = []
        failed = []
        for skill_dir in discovered:
            try:
                result = self.store.install(skill_dir, force=True)
                installed.append(result.name)
            except Exception as e:
                failed.append((skill_dir.name, str(e)))
        return installed, failed

    def _auto_import_examples(self):
        """首次启动时自动导入项目内置示例（仅 examples/ 目录）。"""
        examples_dir = Path(__file__).parent.parent / "examples"
        if not examples_dir.is_dir():
            return
        discovered = self.store.scan_directory(examples_dir)
        if not discovered:
            return
        try:
            installed, failed = self.store.scan_and_install(examples_dir)
            self._refresh_skills()
            names = ", ".join(installed)
            self.show_snack(f"已自动导入 {len(installed)} 个示例 Skill: {names}")
        except Exception:
            logger.exception("Failed to auto-import example skills")

    # ── 健康检查 ──────────────────────────────────────────────

    def _run_health_check(self):
        """运行兼容性扫描并缓存结果。"""
        if self._health_cache is not None:
            return self._health_cache
        from skills_manager.claude_code_checker import ClaudeCodeChecker

        checker = ClaudeCodeChecker()
        reports = checker.scan()
        errors = sum(r.error_count for r in reports)
        warnings = sum(r.warning_count for r in reports)
        self._health_cache = (checker, reports, errors, warnings)
        return self._health_cache

    def _clear_health_cache(self):
        self._health_cache = None

    # ── 更新检查 ──────────────────────────────────────────────

    def _check_for_updates(self):
        """后台检查新版本，发现则提示。"""
        import threading

        def _check():
            try:
                from skills_manager.updater import check_update

                info = check_update()
                if info and info.has_update:
                    self.show_snack(
                        f"Skills Manager v{info.latest_version} 已发布 (当前 v{info.current_version})"
                    )
            except Exception:
                logger.exception("Background update check failed")

        threading.Thread(target=_check, daemon=True).start()

    def _show_update_dialog(self):
        """点击版本号时手动检查更新并显示对话框。"""
        # 先显示检查中
        self.show_snack("正在检查更新...")

        import threading

        def _check_and_show():
            try:
                from skills_manager.updater import check_update

                info = check_update()
                if info is None:
                    summary = "无法检查更新，请检查网络连接"
                    color = ft.Colors.AMBER
                elif info.has_update:
                    summary = f"新版本可用: v{info.latest_version} (当前 v{info.current_version})"
                    color = ft.Colors.AMBER
                    if info.release_url:
                        summary += f"\n下载: {info.release_url}"
                else:
                    summary = f"已是最新版本 v{info.current_version}"
                    color = ft.Colors.GREEN
            except Exception:
                summary = "检查更新失败，请稍后重试"
                color = ft.Colors.ERROR

            dialog = ft.AlertDialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.SYSTEM_UPDATE, color=color),
                        ft.Text(
                            "检查更新", size=FONT_SECTION, weight=ft.FontWeight.BOLD
                        ),
                    ]
                ),
                content=ft.Text(summary, size=FONT_BODY),
                actions=[
                    ft.TextButton(
                        "关闭", on_click=lambda e: self._close_active_dialog()
                    )
                ],
            )
            self._active_dialog = dialog
            self.page.show_dialog(dialog)

        threading.Thread(target=_check_and_show, daemon=True).start()

    def _health_status_color(self):
        _, _, errors, warnings = self._run_health_check()
        if errors > 0:
            return ft.Colors.ERROR
        if warnings > 0:
            return ft.Colors.WARNING
        return ft.Colors.GREEN

    def _health_status_text(self):
        _, _, errors, warnings = self._run_health_check()
        parts = []
        if errors > 0:
            parts.append(f"{errors} 个错误")
        if warnings > 0:
            parts.append(f"{warnings} 个警告")
        if not parts:
            return "健康"
        return "，".join(parts)

    def _show_health_dialog(self):
        self._clear_health_cache()  # 每次打开对话框重新扫描
        checker, reports, errors, warnings = self._run_health_check()
        total = len(reports)
        ok_count = sum(1 for r in reports if r.ok)

        # 摘要行
        if errors == 0 and warnings == 0:
            summary_text = f"共 {total} 个 Skills，全部正常"
            summary_color = ft.Colors.GREEN
        elif errors > 0:
            summary_text = f"共 {total} 个 Skills，{ok_count} 个正常，{errors} 个错误，{warnings} 个警告"
            summary_color = ft.Colors.ERROR
        else:
            summary_text = f"共 {total} 个 Skills，{ok_count} 个正常，{warnings} 个警告"
            summary_color = ft.Colors.AMBER

        # 问题列表
        issue_rows = []
        for r in reports:
            if not r.issues:
                continue
            for issue in r.issues:
                icon = (
                    ft.Icons.ERROR
                    if issue.severity == "error"
                    else ft.Icons.WARNING_AMBER
                )
                color = (
                    ft.Colors.ERROR if issue.severity == "error" else ft.Colors.AMBER
                )
                fixable_note = "  [可自动修复]" if issue.auto_fixable else ""
                issue_rows.append(
                    ft.Row(
                        [
                            ft.Icon(icon, size=14, color=color),
                            ft.Text(
                                f"{r.name}: {issue.message}{fixable_note}",
                                size=FONT_SMALL,
                            ),
                        ],
                        spacing=6,
                    )
                )

        has_fixable = any(i.auto_fixable for r in reports for i in r.issues)

        def do_fix(e):
            fixed = checker.auto_fix(reports)
            self._clear_health_cache()
            self.show_snack(f"已修复 {fixed} 个 Skill")
            # 关闭旧对话框
            self._close_active_dialog()
            # 刷新并重新打开
            self._show_health_dialog()

        actions = [
            ft.TextButton("关闭", on_click=lambda e: self._close_active_dialog())
        ]
        if has_fixable:
            actions.insert(
                0,
                ft.FilledButton(
                    "一键修复", icon=ft.Icons.AUTO_FIX_HIGH, on_click=do_fix
                ),
            )

        dialog = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.HEALTH_AND_SAFETY, color=summary_color),
                    ft.Text("健康检查", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
                ]
            ),
            content=ft.Container(
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text(
                            summary_text,
                            size=FONT_BODY,
                            color=summary_color,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Divider(),
                        ft.Column(
                            spacing=4,
                            controls=issue_rows
                            or [
                                ft.Text(
                                    "没有发现问题",
                                    size=FONT_SMALL,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                )
                            ],
                            scroll=ft.ScrollMode.AUTO,
                            height=min(len(issue_rows) * 30, 300),
                        ),
                    ],
                ),
                width=500,
            ),
            actions=actions,
        )
        self._active_dialog = dialog
        self.page.show_dialog(dialog)

    def _show_install_dialog(self):
        from .dialogs import build_install_dialog

        self._active_dialog = build_install_dialog(self)
        self.page.show_dialog(self._active_dialog)

    def _close_active_dialog(self):
        if self._active_dialog:
            self._active_dialog.open = False
            self.page.update()
            self._active_dialog = None

    # ── 全局快捷键 ────────────────────────────────────────────

    def _on_keyboard(self, e: ft.KeyboardEvent):
        """处理全局键盘快捷键。"""
        # Ctrl+E: 快速导出
        if e.ctrl and e.key == "E" and not e.shift and not e.alt:
            self.navigate("export")
            return

        # Ctrl+F: 聚焦搜索框（跳转到浏览页）
        if e.ctrl and e.key == "F" and not e.shift and not e.alt:
            self.navigate("browse")
            return

        # Ctrl+N: 新建 Skill
        if e.ctrl and e.key == "N" and not e.shift and not e.alt:
            self.navigate("editor")
            return

        # Ctrl+I: 批量导入
        if e.ctrl and e.key == "I" and not e.shift and not e.alt:
            self.navigate("import")
            return

        # Escape: 返回/关闭对话框
        if e.key == "Escape":
            if self._active_dialog:
                self._close_active_dialog()
            elif self.selected_skill_name:
                self.go_back()
            return

    # ── 通用工具 ──────────────────────────────────────────────

    def show_snack(self, text: str, error: bool = False):
        # 清除旧的 SnackBar，避免 overlay 累积
        stale = [c for c in self.page.overlay if isinstance(c, ft.SnackBar)]
        for s in stale:
            self.page.overlay.remove(s)
        snack = ft.SnackBar(
            content=ft.Text(text),
            bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
            duration=3000,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()

    def copy_to_clipboard(self, content: str):
        """复制到系统剪贴板。

        Flet 0.85 重新引入 ``page.clipboard`` Service；若不可用（如旧版本回退）
        则降级为对话框让用户手动复制。
        """
        clipboard = getattr(self.page, "clipboard", None)
        if clipboard is not None and hasattr(clipboard, "set"):
            try:
                clipboard.set(content)
                self.show_snack("已复制到剪贴板")
                return
            except Exception:
                logger.exception("Clipboard set failed, falling back to dialog")

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
            actions=[
                ft.TextButton("关闭", on_click=lambda e: self._close_active_dialog())
            ],
        )
        self._active_dialog = dialog
        self.page.show_dialog(dialog)
