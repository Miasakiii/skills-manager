"""浏览页：搜索栏 + Skill 卡片网格。"""

from __future__ import annotations

import flet as ft

from ..components import EmptyState, SearchBar, SkillCard


def build_browse_page(app) -> ft.Control:
    skills = app.skills

    if not skills:
        return EmptyState(
            on_install=lambda: app._show_install_dialog(),
            on_create=lambda: app.navigate("editor"),
        )

    search_query = getattr(app, "search_query", "").lower().strip()

    # 卡片网格容器（独立引用，搜索时增量更新）
    cards_grid = ft.ResponsiveRow(spacing=12, run_spacing=12)

    def _rebuild_cards():
        q = getattr(app, "search_query", "").lower().strip()
        filtered = skills
        if q:
            filtered = []
            for s in skills:
                text = " ".join([s.name, s.description or "", s.summary or "", " ".join(s.tags or [])]).lower()
                if q in text:
                    filtered.append(s)
        cards_grid.controls = [
            ft.Column(col={"sm": 12, "md": 6, "lg": 4}, controls=[SkillCard(s, on_click=app.show_detail)])
            for s in filtered
        ]
        app.page.update()

    _rebuild_cards()

    def on_search(value: str):
        app.search_query = value
        _rebuild_cards()

    header = ft.Row([
        ft.Text("Skill 库", size=22, weight=ft.FontWeight.BOLD),
        ft.Text(f"{len(skills)} 个已安装", size=13, color=ft.Colors.ON_SURFACE_VARIANT),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    search_bar = SearchBar(on_search=on_search, placeholder="搜索名称、描述、标签...")
    search_bar.content.value = search_query

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[header, search_bar, cards_grid],
    )
