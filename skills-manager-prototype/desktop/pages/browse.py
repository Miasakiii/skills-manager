"""浏览页：搜索栏 + 分类筛选 + Skill 卡片网格。"""

from __future__ import annotations

import flet as ft

from ..components import EmptyState, SearchBar, SkillCard

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

    # 卡片网格容器（独立引用，搜索时增量更新）
    cards_grid = ft.ResponsiveRow(spacing=12, run_spacing=12)

    # 分类筛选芯片容器（独立引用）
    category_chips_row = ft.Row(wrap=True, spacing=8, run_spacing=4)

    def _rebuild_cards():
        q = getattr(app, "search_query", "").lower().strip()
        st = getattr(app, "selected_skill_type", "")
        cat = getattr(app, "selected_category", "")
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
        cards_grid.controls = [
            ft.Column(
                col={"sm": 12, "md": 6, "lg": 4},
                controls=[SkillCard(s, on_click=app.show_detail)],
            )
            for s in filtered
        ]
        app.page.update()

    def _rebuild_category_chips():
        """重建分类筛选芯片。"""
        cat = getattr(app, "selected_category", "")
        category_chips_row.controls.clear()
        for value, label, icon in CATEGORIES:
            is_selected = cat == value

            def make_on_click(v=value):
                return lambda _: on_category_select(v)

            category_chips_row.controls.append(
                ft.Chip(
                    label=ft.Text(label, size=12),
                    leading=ft.Icon(icon, size=16),
                    selected=is_selected,
                    on_click=make_on_click(),
                )
            )

    def _refresh_all():
        _rebuild_category_chips()
        _rebuild_cards()

    _refresh_all()

    def on_search(value: str):
        app.search_query = value
        _rebuild_cards()

    def on_type_select(skill_type: str):
        app.selected_skill_type = skill_type
        _rebuild_cards()

    def on_category_select(category: str):
        app.selected_category = category
        _refresh_all()

    header = ft.Row([
        ft.Text("Skill 库", size=22, weight=ft.FontWeight.BOLD),
        ft.Text(
            f"{len(skills)} 个已安装",
            size=13,
            color=ft.Colors.ON_SURFACE_VARIANT,
        ),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    search_bar = SearchBar(
        on_search=on_search,
        placeholder="搜索名称、描述、标签...",
    )
    search_bar.content.value = search_query

    # 语义类型筛选芯片
    type_chips = ft.Row(
        spacing=8,
        controls=[
            ft.Chip(
                label=ft.Text("全部类型"),
                selected=selected_skill_type == "",
                on_click=lambda _: on_type_select(""),
            ),
            ft.Chip(
                label=ft.Text("模板"),
                selected=selected_skill_type == "component",
                on_click=lambda _: on_type_select("component"),
            ),
            ft.Chip(
                label=ft.Text("对话"),
                selected=selected_skill_type == "interactive",
                on_click=lambda _: on_type_select("interactive"),
            ),
            ft.Chip(
                label=ft.Text("流程"),
                selected=selected_skill_type == "workflow",
                on_click=lambda _: on_type_select("workflow"),
            ),
        ],
    )

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            header,
            search_bar,
            ft.Text("分类筛选", size=13, weight=ft.FontWeight.BOLD),
            category_chips_row,
            ft.Text("类型筛选", size=13, weight=ft.FontWeight.BOLD),
            type_chips,
            ft.Divider(),
            cards_grid,
        ],
    )
