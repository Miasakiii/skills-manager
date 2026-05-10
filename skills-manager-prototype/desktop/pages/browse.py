"""浏览页：搜索栏 + 分类筛选 + 排序 + Skill 卡片网格。"""

from __future__ import annotations

import asyncio

import flet as ft

from ..components import (
    EmptyState, FilterEmptyState, RecentUsage, SearchBar,
    SearchEmptyState, SkillCard, SkillListItem, TagCloud,
    FONT_TITLE, FONT_SUBTITLE, FONT_SECTION,
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


def _parse_version(v: str) -> tuple:
    """安全解析版本号为可比较的元组，解析失败返回 (0,)。"""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except (ValueError, AttributeError):
        return (0,)


def build_browse_page(app) -> ft.Control:
    skills = app.skills

    if not skills:
        return EmptyState(
            on_install=lambda: app._show_install_dialog(),
            on_create=lambda: app.navigate("editor"),
        )

    search_query = getattr(app, "search_query", "").lower().strip()
    selected_skill_type = getattr(app, "selected_skill_type", "")
    selected_category = getattr(app, "selected_category", "")
    selected_tag = getattr(app, "selected_tag", "")
    sort_by = getattr(app, "sort_by", "name_asc")
    view_mode = getattr(app, "view_mode", "grid")  # "grid" | "list"
    batch_mode = getattr(app, "batch_mode", False)
    compact_mode = getattr(app, "compact_mode", True)
    checked_skills = getattr(app, "checked_skills", set())

    # 内容容器（独立引用，搜索/切换视图时增量更新）
    content_container = ft.Column(spacing=8)

    # 分类筛选芯片容器（独立引用）
    category_chips_row = ft.Row(wrap=True, spacing=8, run_spacing=4)

    # 标签云容器（独立引用）
    tag_cloud_container = ft.Column(spacing=8)

    # 最近使用容器（独立引用）
    recent_usage_container = ft.Column(spacing=8)

    # 批量操作栏容器（独立引用）
    batch_bar_container = ft.Column(spacing=0)

    def _sort_skills(skill_list: list) -> list:
        """按当前排序方式排列 Skill 列表。"""
        key = sort_by
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

    def _filter_skills() -> list:
        """根据当前筛选条件过滤 Skill 列表。"""
        q = getattr(app, "search_query", "").lower().strip()
        st = getattr(app, "selected_skill_type", "")
        cat = getattr(app, "selected_category", "")
        tag = getattr(app, "selected_tag", "")
        filtered = skills
        if q:
            filtered = []
            for s in skills:
                text = " ".join([
                    s.name, s.description or "",
                    s.summary or "", " ".join(s.tags or []),
                ]).lower()
                if q in text:
                    filtered.append(s)
        if st:
            filtered = [
                s for s in filtered
                if getattr(s, 'skill_type', '') == st
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

    def _build_list_items(skill_list: list, bm: bool, cm: bool, checked: set) -> list:
        """构建列表视图项。"""
        return [
            SkillListItem(s, on_click=app.show_detail, checkbox_mode=bm,
                          checked=s.name in checked, on_check=on_skill_check, compact=cm)
            for s in skill_list
        ]

    def _build_grid_items(skill_list: list, bm: bool, cm: bool, checked: set) -> ft.ResponsiveRow:
        """构建网格视图项。"""
        grid = ft.ResponsiveRow(spacing=12, run_spacing=12)
        grid.controls = [
            ft.Column(col={"sm": 12, "md": 6, "lg": 4},
                      controls=[SkillCard(s, on_click=app.show_detail, checkbox_mode=bm,
                                          checked=s.name in checked, on_check=on_skill_check, compact=cm)])
            for s in skill_list
        ]
        return grid

    def _rebuild_cards():
        q = getattr(app, "search_query", "").lower().strip()
        st = getattr(app, "selected_skill_type", "")
        cat = getattr(app, "selected_category", "")
        tag = getattr(app, "selected_tag", "")
        sort_by = getattr(app, "sort_by", "name_asc")
        vm = getattr(app, "view_mode", "grid")
        bm = getattr(app, "batch_mode", False)
        cm = getattr(app, "compact_mode", True)
        checked = getattr(app, "checked_skills", set())
        filtered = _filter_skills()
        filtered = _sort_skills(filtered)

        # 空状态处理
        if not filtered:
            def clear_all_filters():
                app.search_query = ""
                app.selected_skill_type = ""
                app.selected_category = ""
                app.selected_tag = ""
                _refresh_all()

            if q:
                content_container.controls = [SearchEmptyState(query=q, on_clear=clear_all_filters)]
            elif st or cat or tag:
                content_container.controls = [FilterEmptyState(on_clear=clear_all_filters)]
            else:
                content_container.controls = [SearchEmptyState(query=q, on_clear=clear_all_filters)]
        else:
            # 判断是否启用分区展示：排序为"按分类"且未选中特定分类
            use_sections = sort_by == "category" and not cat

            if use_sections:
                # 按分类分组
                grouped = {}
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
                        ft.Text(f"{cat_label}（{len(skill_list)}）", size=15, weight=ft.FontWeight.BOLD),
                    ], spacing=8)

                    if vm == "list":
                        items = _build_list_items(skill_list, bm, cm, checked)
                        sections.append(ft.Column(spacing=8, controls=[section_title] + items))
                    else:
                        grid = _build_grid_items(skill_list, bm, cm, checked)
                        sections.append(ft.Column(spacing=8, controls=[section_title, grid]))

                content_container.controls = sections
            elif vm == "list":
                content_container.controls = _build_list_items(filtered, bm, cm, checked)
            else:
                content_container.controls = [_build_grid_items(filtered, bm, cm, checked)]
        app.page.update()

    def _rebuild_category_chips():
        """重建分类筛选芯片。"""
        cat = getattr(app, "selected_category", "")
        category_chips_row.controls.clear()
        for value, label, icon in CATEGORIES:
            is_selected = cat == value

            def make_on_click(v=value):
                return lambda _: on_category_select(v)

            chip = ft.Chip(
                label=ft.Text(label, size=12),
                leading=ft.Icon(icon, size=16),
                selected=is_selected,
                on_click=make_on_click(),
            )

            # "全部"芯片旁显示已安装总数
            if value == "":
                badge = ft.Container(
                    content=ft.Text(str(len(skills)), size=10, color=ft.Colors.ON_PRIMARY),
                    bgcolor=ft.Colors.PRIMARY,
                    border_radius=10,
                    padding=ft.Padding(6, 1, 6, 1),
                )
                category_chips_row.controls.append(
                    ft.Row([chip, badge], spacing=2, tight=True)
                )
            else:
                category_chips_row.controls.append(chip)

    def _rebuild_tag_cloud():
        """重建标签云。"""
        tag = getattr(app, "selected_tag", "")
        tag_cloud_container.controls = [
            TagCloud(
                skills=skills,
                selected_tag=tag,
                on_tag_click=on_tag_select,
            )
        ]

    def _rebuild_recent_usage():
        """重建最近使用区域。"""
        recent_names = app.store.get_recent_skills(limit=5)
        recent_skills = [s for s in skills if s.name in recent_names]
        # 按最近使用顺序排列
        name_order = {n: i for i, n in enumerate(recent_names)}
        recent_skills.sort(key=lambda s: name_order.get(s.name, 999))
        favorites = app.store.get_favorites()

        recent_usage_container.controls = [
            RecentUsage(
                recent_skills=recent_skills,
                favorites=favorites,
                on_skill_click=lambda name: app.show_detail(name),
                on_favorite_toggle=on_favorite_toggle,
            )
        ]

    # 语义类型筛选芯片（容器引用，支持动态重建）
    type_chips_row = ft.Row(spacing=8)

    def _rebuild_type_chips():
        """重建类型筛选芯片。"""
        st = getattr(app, "selected_skill_type", "")
        TYPES = [
            ("", "全部类型", ft.Icons.LAYERS),
            ("component", "模板", ft.Icons.DESCRIPTION),
            ("interactive", "对话", ft.Icons.CHAT),
            ("workflow", "流程", ft.Icons.ACCOUNT_TREE),
        ]
        type_chips_row.controls.clear()
        for value, label, icon in TYPES:
            def make_on_click(v=value):
                return lambda _: on_type_select(v)
            type_chips_row.controls.append(
                ft.Chip(
                    label=ft.Text(label, size=12),
                    leading=ft.Icon(icon, size=16),
                    selected=st == value,
                    on_click=make_on_click(),
                )
            )

    def on_search(value: str):
        app.search_query = value
        _rebuild_cards()

    def on_type_select(skill_type: str):
        app.selected_skill_type = skill_type
        _rebuild_type_chips()
        _rebuild_cards()

    def on_category_select(category: str):
        app.selected_category = category
        _refresh_all()

    def on_tag_select(tag: str):
        app.selected_tag = tag
        _refresh_all()

    def on_favorite_toggle(name: str):
        app.store.toggle_favorite(name)
        _refresh_all()

    def on_skill_check(name: str, checked: bool):
        """切换 Skill 选中状态。"""
        checked_set = getattr(app, "checked_skills", set())
        if checked:
            checked_set.add(name)
        else:
            checked_set.discard(name)
        app.checked_skills = checked_set
        _rebuild_batch_bar()
        app.page.update()

    def _refresh_all():
        _rebuild_category_chips()
        _rebuild_type_chips()
        _rebuild_tag_cloud()
        _rebuild_recent_usage()
        _rebuild_cards()

    _refresh_all()

    def on_toggle_batch_mode():
        """切换批量选择模式。"""
        app.batch_mode = not getattr(app, "batch_mode", False)
        if not app.batch_mode:
            app.checked_skills = set()
        _rebuild_batch_bar()
        _rebuild_cards()

    def on_select_all():
        """全选当前筛选结果。"""
        filtered = _filter_skills()
        app.checked_skills = {s.name for s in filtered}
        _rebuild_batch_bar()
        _rebuild_cards()

    def on_deselect_all():
        """取消全选。"""
        app.checked_skills = set()
        _rebuild_batch_bar()
        _rebuild_cards()

    def on_batch_export():
        """批量导出选中的 Skill。"""
        checked = getattr(app, "checked_skills", set())
        if not checked:
            app.show_snack("请先选择要导出的 Skill", error=True)
            return
        # 跳转到导出页，传递选中的 Skill 列表
        app.batch_export_skills = list(checked)
        app.navigate("export")

    def on_batch_uninstall():
        """批量卸载选中的 Skill。"""
        checked = getattr(app, "checked_skills", set())
        if not checked:
            app.show_snack("请先选择要卸载的 Skill", error=True)
            return
        # 显示确认对话框
        from ..dialogs import build_batch_uninstall_dialog
        app._active_dialog = build_batch_uninstall_dialog(app, list(checked))
        app.page.show_dialog(app._active_dialog)

    def _rebuild_batch_bar():
        """重建批量操作栏。"""
        bm = getattr(app, "batch_mode", False)
        checked = getattr(app, "checked_skills", set())
        if not bm:
            batch_bar_container.controls = []
            return
        batch_bar_container.controls = [
            ft.Container(
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                border_radius=8,
                padding=ft.Padding(12, 8, 12, 8),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row([
                            ft.Text(f"已选择 {len(checked)} 个 Skill", size=13),
                            ft.TextButton("全选", on_click=lambda _: on_select_all()),
                            ft.TextButton("取消全选", on_click=lambda _: on_deselect_all()),
                        ], spacing=8),
                        ft.Row([
                            ft.FilledButton(
                                "批量导出",
                                icon=ft.Icons.FILE_DOWNLOAD,
                                on_click=lambda _: on_batch_export(),
                            ),
                            ft.OutlinedButton(
                                "批量卸载",
                                icon=ft.Icons.DELETE,
                                on_click=lambda _: on_batch_uninstall(),
                            ),
                            ft.TextButton(
                                "退出批量模式",
                                on_click=lambda _: on_toggle_batch_mode(),
                            ),
                        ], spacing=8),
                    ],
                ),
            ),
        ]

    def on_sort_change(e):
        app.sort_by = e.control.value
        _rebuild_cards()

    def on_view_change(mode: str):
        app.view_mode = mode
        _update_view_buttons()
        _rebuild_cards()

    # 排序下拉框
    sort_dropdown = ft.Dropdown(
        value=sort_by,
        options=[ft.dropdown.Option(key=k, text=v) for k, v in SORT_OPTIONS],
        on_select=on_sort_change,
        width=140,
        text_size=12,
        border_radius=8,
        content_padding=ft.Padding(8, 4, 8, 4),
    )

    # 视图切换按钮
    grid_btn = ft.IconButton(
        icon=ft.Icons.GRID_VIEW,
        icon_size=20,
        tooltip="网格视图",
        selected=view_mode == "grid",
        on_click=lambda _: on_view_change("grid"),
    )
    list_btn = ft.IconButton(
        icon=ft.Icons.VIEW_LIST,
        icon_size=20,
        tooltip="列表视图",
        selected=view_mode == "list",
        on_click=lambda _: on_view_change("list"),
    )

    def _update_view_buttons():
        vm = getattr(app, "view_mode", "grid")
        grid_btn.selected = vm == "grid"
        list_btn.selected = vm == "list"

    # 批量模式切换按钮
    batch_btn = ft.IconButton(
        icon=ft.Icons.CHECKLIST,
        icon_size=20,
        tooltip="批量操作",
        selected=batch_mode,
        on_click=lambda _: on_toggle_batch_mode(),
    )

    # 简洁/详细模式切换按钮
    def on_toggle_compact():
        app.compact_mode = not getattr(app, "compact_mode", True)
        compact_btn.icon = ft.Icons.VIEW_COMPACT if app.compact_mode else ft.Icons.VIEW_AGENDA
        compact_btn.tooltip = "简洁模式" if app.compact_mode else "详细模式"
        _rebuild_cards()

    compact_btn = ft.IconButton(
        icon=ft.Icons.VIEW_COMPACT if compact_mode else ft.Icons.VIEW_AGENDA,
        icon_size=20,
        tooltip="简洁模式" if compact_mode else "详细模式",
        on_click=lambda _: on_toggle_compact(),
    )

    header = ft.Row([
        ft.Text("Skill 库", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
        ft.Row([
            ft.Text(
                f"{len(skills)} 个已安装",
                size=FONT_SUBTITLE,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            sort_dropdown,
            compact_btn,
            grid_btn,
            list_btn,
            batch_btn,
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    search_bar = SearchBar(
        on_search=on_search,
        placeholder="搜索名称、描述、标签...",
    )
    search_bar.content.value = search_query

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            header,
            batch_bar_container,
            recent_usage_container,
            search_bar,
            ft.Text("分类筛选", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            category_chips_row,
            ft.Text("类型筛选", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            type_chips_row,
            tag_cloud_container,
            ft.Divider(),
            content_container,
        ],
    )
