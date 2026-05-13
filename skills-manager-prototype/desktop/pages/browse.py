"""浏览页：搜索栏 + 分类筛选 + 排序 + Skill 卡片网格。"""

from __future__ import annotations

import flet as ft

from ..components import (
    EmptyState, FilterEmptyState, RecentUsage, SearchBar,
    SearchEmptyState, SkillCard, SkillListItem, TagCloud,
    FONT_TITLE, FONT_SUBTITLE, FONT_SECTION, FONT_BODY, FONT_SMALL,
)

# 一级分类定义
CATEGORIES = [
    ("", "全部", ft.Icons.APPS),
    ("language", "语言处理", ft.Icons.TRANSLATE),
    ("code", "编程开发", ft.Icons.CODE),
    ("data", "数据分析", ft.Icons.ANALYTICS),
    ("research", "信息检索", ft.Icons.SEARCH),
    ("writing", "内容创作", ft.Icons.EDIT),
    ("automation", "流程自动化", ft.Icons.SETTINGS),
    ("agent", "Agent 增强", ft.Icons.SMART_TOY),
    ("misc", "其他", ft.Icons.EXTENSION),
]

# 排序选项
SORT_OPTIONS = [
    ("name_asc", "名称 A-Z"),
    ("installed_desc", "最近安装"),
    ("version_desc", "版本更新"),
    ("category", "按分类"),
]

# 语义类型定义
_SKILL_TYPES = [
    ("", "全部类型", ft.Icons.LAYERS),
    ("component", "模板", ft.Icons.DESCRIPTION),
    ("interactive", "对话", ft.Icons.CHAT),
    ("workflow", "流程", ft.Icons.ACCOUNT_TREE),
]


def _parse_version(v: str) -> tuple:
    """安全解析版本号为可比较的元组，解析失败返回 (0,)。"""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except (ValueError, AttributeError):
        return (0,)


class BrowsePage:
    """浏览页：搜索、筛选、排序、卡片网格。"""

    def __init__(self, app) -> None:
        self.app = app
        self.skills = app.skills

        # 内容容器（独立引用，支持增量更新）
        self.content_container = ft.Column(spacing=8)
        self.category_chips_row = ft.Row(wrap=True, spacing=8, run_spacing=4)
        self.tag_cloud_container = ft.Column(spacing=8)
        self.recent_usage_container = ft.Column(spacing=8)
        self.batch_bar_container = ft.Column(spacing=0)
        self.type_chips_row = ft.Row(spacing=8)

        # 视图控件引用
        self._sort_dropdown: ft.Dropdown | None = None
        self._grid_btn: ft.IconButton | None = None
        self._list_btn: ft.IconButton | None = None
        self._batch_btn: ft.IconButton | None = None
        self._compact_btn: ft.IconButton | None = None

    def _get_state(self, attr: str, default=""):
        """从 app 读取状态属性。"""
        return getattr(self.app, attr, default)

    # ── 排序与过滤 ──

    def _sort_skills(self, skill_list: list) -> list:
        """按当前排序方式排列 Skill 列表。"""
        key = self._get_state("sort_by", "name_asc")
        if key == "name_asc":
            return sorted(skill_list, key=lambda s: s.name.lower())
        if key == "installed_desc":
            return sorted(
                skill_list,
                key=lambda s: getattr(s, "installed_at", "") or "",
                reverse=True,
            )
        if key == "version_desc":
            return sorted(
                skill_list,
                key=lambda s: _parse_version(getattr(s, "version", "0")),
                reverse=True,
            )
        if key == "category":
            return sorted(skill_list, key=lambda s: (s.category or "misc", s.name.lower()))
        return skill_list

    def _filter_skills(self) -> list:
        """根据当前筛选条件过滤 Skill 列表。"""
        q = self._get_state("search_query", "").lower().strip()
        st = self._get_state("selected_skill_type", "")
        cat = self._get_state("selected_category", "")
        tag = self._get_state("selected_tag", "")
        filtered = self.skills
        if q:
            filtered = []
            for s in self.skills:
                text = " ".join([
                    s.name, s.description or "",
                    s.summary or "", " ".join(s.tags or []),
                ]).lower()
                if q in text:
                    filtered.append(s)
        if st:
            filtered = [
                s for s in filtered
                if getattr(s, "skill_type", "") == st
            ]
        if cat:
            filtered = [
                s for s in filtered
                if (s.category or "misc") == cat
            ]
        if tag:
            filtered = [
                s for s in filtered
                if tag in (getattr(s, "tags", None) or [])
            ]
        return filtered

    # ── 视图构建 ──

    def _build_list_items(self, skill_list: list, bm: bool, cm: bool, checked: set) -> list:
        """构建列表视图项。"""
        return [
            SkillListItem(
                s, on_click=self.app.show_detail, checkbox_mode=bm,
                checked=s.name in checked, on_check=self._on_skill_check, compact=cm,
            )
            for s in skill_list
        ]

    def _build_grid_items(self, skill_list: list, bm: bool, cm: bool, checked: set) -> ft.ResponsiveRow:
        """构建网格视图项。"""
        grid = ft.ResponsiveRow(spacing=12, run_spacing=12)
        grid.controls = [
            ft.Column(
                col={"sm": 12, "md": 6, "lg": 4},
                controls=[SkillCard(
                    s, on_click=self.app.show_detail, checkbox_mode=bm,
                    checked=s.name in checked, on_check=self._on_skill_check, compact=cm,
                )],
            )
            for s in skill_list
        ]
        return grid

    # ── 重建子区域 ──

    def _rebuild_cards(self):
        q = self._get_state("search_query", "").lower().strip()
        st = self._get_state("selected_skill_type", "")
        cat = self._get_state("selected_category", "")
        tag = self._get_state("selected_tag", "")
        sort_by = self._get_state("sort_by", "name_asc")
        vm = self._get_state("view_mode", "grid")
        bm = self._get_state("batch_mode", False)
        cm = self._get_state("compact_mode", True)
        checked = self._get_state("checked_skills", set())
        filtered = self._filter_skills()
        filtered = self._sort_skills(filtered)

        if not filtered:
            self._show_empty_state(q, st, cat, tag)
        else:
            use_sections = sort_by == "category" and not cat
            if use_sections:
                self._show_grouped(filtered, vm, bm, cm, checked)
            elif vm == "list":
                self.content_container.controls = self._build_list_items(filtered, bm, cm, checked)
            else:
                self.content_container.controls = [self._build_grid_items(filtered, bm, cm, checked)]
        self.app.page.update()

    def _show_empty_state(self, q: str, st: str, cat: str, tag: str):
        """显示空状态。"""
        def clear_all_filters():
            self.app.search_query = ""
            self.app.selected_skill_type = ""
            self.app.selected_category = ""
            self.app.selected_tag = ""
            self._refresh_all()

        if q:
            self.content_container.controls = [SearchEmptyState(query=q, on_clear=clear_all_filters)]
        elif st or cat or tag:
            self.content_container.controls = [FilterEmptyState(on_clear=clear_all_filters)]
        else:
            self.content_container.controls = [SearchEmptyState(query=q, on_clear=clear_all_filters)]

    def _show_grouped(self, filtered: list, vm: str, bm: bool, cm: bool, checked: set):
        """按分类分组展示。"""
        grouped: dict[str, list] = {}
        for s in filtered:
            key = s.category or "misc"
            grouped.setdefault(key, []).append(s)

        sections = []
        for cat_key, cat_label, cat_icon in CATEGORIES[1:]:  # 跳过"全部"
            if cat_key not in grouped:
                continue
            skill_list = grouped[cat_key]
            section_title = ft.Row([
                ft.Icon(cat_icon, size=20, color=ft.Colors.PRIMARY),
                ft.Text(f"{cat_label}（{len(skill_list)}）", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            ], spacing=8)

            if vm == "list":
                items = self._build_list_items(skill_list, bm, cm, checked)
                sections.append(ft.Column(spacing=8, controls=[section_title] + items))
            else:
                grid = self._build_grid_items(skill_list, bm, cm, checked)
                sections.append(ft.Column(spacing=8, controls=[section_title, grid]))

        self.content_container.controls = sections

    def _rebuild_category_chips(self):
        """重建分类筛选芯片。"""
        cat = self._get_state("selected_category", "")
        self.category_chips_row.controls.clear()
        for value, label, icon in CATEGORIES:
            is_selected = cat == value
            def _make_cat_handler(v=value):
                return lambda _e: self._on_category_select(v)
            chip = ft.Chip(
                label=ft.Text(label, size=FONT_SMALL),
                leading=ft.Icon(icon, size=16),
                selected=is_selected,
                on_click=_make_cat_handler(),
            )
            if value == "":
                badge = ft.Container(
                    content=ft.Text(str(len(self.skills)), size=FONT_SMALL, color=ft.Colors.ON_PRIMARY),
                    bgcolor=ft.Colors.PRIMARY,
                    border_radius=10,
                    padding=ft.Padding(6, 1, 6, 1),
                )
                self.category_chips_row.controls.append(
                    ft.Row([chip, badge], spacing=2, tight=True)
                )
            else:
                self.category_chips_row.controls.append(chip)

    def _rebuild_type_chips(self):
        """重建类型筛选芯片。"""
        st = self._get_state("selected_skill_type", "")
        self.type_chips_row.controls.clear()
        for value, label, icon in _SKILL_TYPES:
            def _make_type_handler(v=value):
                return lambda _e: self._on_type_select(v)
            self.type_chips_row.controls.append(
                ft.Chip(
                    label=ft.Text(label, size=FONT_SMALL),
                    leading=ft.Icon(icon, size=16),
                    selected=st == value,
                    on_click=_make_type_handler(),
                )
            )

    def _rebuild_tag_cloud(self):
        """重建标签云。"""
        tag = self._get_state("selected_tag", "")
        self.tag_cloud_container.controls = [
            TagCloud(
                skills=self.skills,
                selected_tag=tag,
                on_tag_click=self._on_tag_select,
            )
        ]

    def _rebuild_recent_usage(self):
        """重建最近使用区域。"""
        recent_names = self.app.store.get_recent_skills(limit=5)
        recent_skills = [s for s in self.skills if s.name in recent_names]
        name_order = {n: i for i, n in enumerate(recent_names)}
        recent_skills.sort(key=lambda s: name_order.get(s.name, 999))
        favorites = self.app.store.get_favorites()

        self.recent_usage_container.controls = [
            RecentUsage(
                recent_skills=recent_skills,
                favorites=favorites,
                on_skill_click=lambda name: self.app.show_detail(name),
                on_favorite_toggle=self._on_favorite_toggle,
            )
        ]

    def _rebuild_batch_bar(self):
        """重建批量操作栏。"""
        bm = self._get_state("batch_mode", False)
        checked = self._get_state("checked_skills", set())
        if not bm:
            self.batch_bar_container.controls = []
            return
        self.batch_bar_container.controls = [
            ft.Container(
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=8,
                padding=ft.Padding(12, 8, 12, 8),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row([
                            ft.Text(f"已选择 {len(checked)} 个 Skill", size=FONT_BODY),
                            ft.TextButton("全选", on_click=lambda _: self._on_select_all()),
                            ft.TextButton("取消全选", on_click=lambda _: self._on_deselect_all()),
                        ], spacing=8),
                        ft.Row([
                            ft.FilledButton(
                                "批量导出",
                                icon=ft.Icons.FILE_DOWNLOAD,
                                on_click=lambda _: self._on_batch_export(),
                            ),
                            ft.OutlinedButton(
                                "批量卸载",
                                icon=ft.Icons.DELETE,
                                on_click=lambda _: self._on_batch_uninstall(),
                            ),
                            ft.TextButton(
                                "退出批量模式",
                                on_click=lambda _: self._on_toggle_batch_mode(),
                            ),
                        ], spacing=8),
                    ],
                ),
            ),
        ]

    # ── 事件处理 ──

    def _on_search(self, value: str):
        self.app.search_query = value
        self._rebuild_cards()

    def _on_type_select(self, skill_type: str):
        self.app.selected_skill_type = skill_type
        self._rebuild_type_chips()
        self._rebuild_cards()

    def _on_category_select(self, category: str):
        self.app.selected_category = category
        self._refresh_all()

    def _on_tag_select(self, tag: str):
        self.app.selected_tag = tag
        self._refresh_all()

    def _on_favorite_toggle(self, name: str):
        self.app.store.toggle_favorite(name)
        self._refresh_all()

    def _on_skill_check(self, name: str, checked: bool):
        """切换 Skill 选中状态。"""
        checked_set = self._get_state("checked_skills", set())
        if checked:
            checked_set.add(name)
        else:
            checked_set.discard(name)
        self.app.checked_skills = checked_set
        self._rebuild_batch_bar()
        self.app.page.update()

    def _on_toggle_batch_mode(self):
        """切换批量选择模式。"""
        self.app.batch_mode = not self._get_state("batch_mode", False)
        if not self.app.batch_mode:
            self.app.checked_skills = set()
        self._rebuild_batch_bar()
        self._rebuild_cards()

    def _on_select_all(self):
        """全选当前筛选结果。"""
        filtered = self._filter_skills()
        self.app.checked_skills = {s.name for s in filtered}
        self._rebuild_batch_bar()
        self._rebuild_cards()

    def _on_deselect_all(self):
        """取消全选。"""
        self.app.checked_skills = set()
        self._rebuild_batch_bar()
        self._rebuild_cards()

    def _on_batch_export(self):
        """批量导出选中的 Skill。"""
        checked = self._get_state("checked_skills", set())
        if not checked:
            self.app.show_snack("请先选择要导出的 Skill", error=True)
            return
        self.app.batch_export_skills = list(checked)
        self.app.navigate("export")

    def _on_batch_uninstall(self):
        """批量卸载选中的 Skill。"""
        checked = self._get_state("checked_skills", set())
        if not checked:
            self.app.show_snack("请先选择要卸载的 Skill", error=True)
            return
        from ..dialogs import build_batch_uninstall_dialog
        self.app._active_dialog = build_batch_uninstall_dialog(self.app, list(checked))
        self.app.page.show_dialog(self.app._active_dialog)

    def _on_sort_change(self, e):
        self.app.sort_by = e.control.value
        self._rebuild_cards()

    def _on_view_change(self, mode: str):
        self.app.view_mode = mode
        self._update_view_buttons()
        self._rebuild_cards()

    def _on_toggle_compact(self):
        self.app.compact_mode = not self._get_state("compact_mode", True)
        if self._compact_btn:
            self._compact_btn.icon = (
                ft.Icons.VIEW_COMPACT if self.app.compact_mode else ft.Icons.VIEW_AGENDA
            )
            self._compact_btn.tooltip = "简洁模式" if self.app.compact_mode else "详细模式"
        self._rebuild_cards()

    def _update_view_buttons(self):
        vm = self._get_state("view_mode", "grid")
        if self._grid_btn:
            self._grid_btn.selected = vm == "grid"
        if self._list_btn:
            self._list_btn.selected = vm == "list"

    def _refresh_all(self):
        self._rebuild_category_chips()
        self._rebuild_type_chips()
        self._rebuild_tag_cloud()
        self._rebuild_recent_usage()
        self._rebuild_cards()

    # ── 页面组装 ──

    def _build_header(self) -> ft.Row:
        sort_by = self._get_state("sort_by", "name_asc")
        view_mode = self._get_state("view_mode", "grid")
        batch_mode = self._get_state("batch_mode", False)
        compact_mode = self._get_state("compact_mode", True)

        self._sort_dropdown = ft.Dropdown(
            value=sort_by,
            options=[ft.dropdown.Option(key=k, text=v) for k, v in SORT_OPTIONS],
            on_select=self._on_sort_change,
            width=140,
            text_size=FONT_BODY,
            border_radius=8,
            content_padding=ft.Padding(8, 4, 8, 4),
        )

        self._grid_btn = ft.IconButton(
            icon=ft.Icons.GRID_VIEW,
            icon_size=20,
            tooltip="网格视图",
            selected=view_mode == "grid",
            on_click=lambda _: self._on_view_change("grid"),
        )
        self._list_btn = ft.IconButton(
            icon=ft.Icons.VIEW_LIST,
            icon_size=20,
            tooltip="列表视图",
            selected=view_mode == "list",
            on_click=lambda _: self._on_view_change("list"),
        )
        self._batch_btn = ft.IconButton(
            icon=ft.Icons.CHECKLIST,
            icon_size=20,
            tooltip="批量操作",
            selected=batch_mode,
            on_click=lambda _: self._on_toggle_batch_mode(),
        )
        self._compact_btn = ft.IconButton(
            icon=ft.Icons.VIEW_COMPACT if compact_mode else ft.Icons.VIEW_AGENDA,
            icon_size=20,
            tooltip="简洁模式" if compact_mode else "详细模式",
            on_click=lambda _: self._on_toggle_compact(),
        )

        return ft.Row([
            ft.Text("Skill 库", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Text(
                    f"{len(self.skills)} 个已安装",
                    size=FONT_SUBTITLE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                self._sort_dropdown,
                self._compact_btn,
                self._grid_btn,
                self._list_btn,
                self._batch_btn,
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def build(self) -> ft.Control:
        """构建并返回浏览页控件。"""
        if not self.skills:
            return EmptyState(
                on_install=lambda: self.app._show_install_dialog(),
                on_create=lambda: self.app.navigate("editor"),
            )

        self._refresh_all()

        search_query = self._get_state("search_query", "")
        search_bar = SearchBar(
            on_search=self._on_search,
            placeholder="搜索名称、描述、标签...",
        )
        search_bar.content.value = search_query

        return ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            expand=True,
            controls=[
                self._build_header(),
                self.batch_bar_container,
                self.recent_usage_container,
                search_bar,
                ft.Text("分类筛选", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
                self.category_chips_row,
                ft.Text("类型筛选", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
                self.type_chips_row,
                self.tag_cloud_container,
                ft.Divider(),
                self.content_container,
            ],
        )


def build_browse_page(app) -> ft.Control:
    """构建浏览页（兼容旧接口）。"""
    return BrowsePage(app).build()
