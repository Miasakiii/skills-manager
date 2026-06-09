"""最近活动 + 使用频率统计页面。"""

from __future__ import annotations

import flet as ft

from ..components import (
    FONT_BODY,
    FONT_CARD_DESC,
    FONT_CARD_NAME,
    FONT_META,
    FONT_SECTION,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)
from ..theme import COLORS, RADIUS_MD


WINDOW_DAYS = 30  # 频率统计窗口


def build_recommend_page(app) -> ft.Control:
    """构建最近活动 + 频率排行页面。"""
    skills = app.skills

    if not skills:
        from ..components import EmptyState

        return EmptyState(
            on_install=lambda: app._show_install_dialog(),
            on_create=lambda: app.navigate("editor"),
        )

    skill_lookup = {s.name: s for s in skills}

    recent_names = app.store.get_recent_skills(limit=10)
    export_history = app.store.get_export_history()
    top_skills = app.store.get_top_skills(limit=8, window_days=WINDOW_DAYS)
    format_stats = app.store.get_export_format_stats(window_days=WINDOW_DAYS)

    # ── 热门 Skill 卡片 ──
    top_controls: list[ft.Control] = []
    if top_skills:
        max_score = max(score for _, score in top_skills) or 1
        for idx, (name, score) in enumerate(top_skills, start=1):
            info = skill_lookup.get(name)
            label = info.description if info else "（已卸载）"
            top_controls.append(
                _rank_row(
                    idx=idx,
                    name=name,
                    score=score,
                    max_score=max_score,
                    description=label,
                    on_click=(lambda _, n=name: app.show_detail(n))
                    if info
                    else None,
                )
            )
    else:
        top_controls.append(
            ft.Text(
                f"最近 {WINDOW_DAYS} 天没有使用或导出记录",
                size=FONT_SUBTITLE,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )

    # ── 导出格式占比 ──
    format_controls: list[ft.Control] = []
    if format_stats:
        total = sum(count for _, count in format_stats) or 1
        for fmt, count in format_stats:
            ratio = count / total
            format_controls.append(_format_row(fmt, count, ratio))
    else:
        format_controls.append(
            ft.Text(
                f"最近 {WINDOW_DAYS} 天没有导出记录",
                size=FONT_SUBTITLE,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )

    # ── 最近使用 ──
    recent_controls: list[ft.Control] = []
    if recent_names:
        for name in recent_names:
            info = skill_lookup.get(name)
            if info:
                recent_controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.HISTORY, size=20),
                        title=ft.Text(
                            info.name,
                            size=FONT_CARD_NAME,
                            weight=ft.FontWeight.BOLD,
                        ),
                        subtitle=ft.Text(
                            info.description or info.summary or "",
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
            ft.Text(
                "暂无使用记录",
                size=FONT_SUBTITLE,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )

    # ── 最近导出 ──
    export_controls: list[ft.Control] = []
    recent_exports = export_history[-10:] if export_history else []
    if recent_exports:
        for entry in reversed(recent_exports):
            export_controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.FILE_DOWNLOAD, size=20),
                    title=ft.Text(
                        entry.get("skill_name", ""), size=FONT_CARD_NAME
                    ),
                    subtitle=ft.Text(
                        f"{entry.get('format', '')}  ·  {entry.get('output_path', '')}",
                        size=FONT_CARD_DESC,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                )
            )
    else:
        export_controls.append(
            ft.Text(
                "暂无导出记录",
                size=FONT_SUBTITLE,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        expand=True,
        controls=[
            ft.Text("最近活动", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
            ft.Text(
                f"过去 {WINDOW_DAYS} 天的使用与导出统计",
                size=FONT_SUBTITLE,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Divider(),
            _section_header(ft.Icons.LOCAL_FIRE_DEPARTMENT, "热门 Skill"),
            ft.Card(
                content=ft.Container(
                    padding=ft.Padding(12, 12, 12, 12),
                    content=ft.Column(spacing=10, controls=top_controls),
                )
            ),
            _section_header(ft.Icons.PIE_CHART, "导出格式分布"),
            ft.Card(
                content=ft.Container(
                    padding=ft.Padding(12, 12, 12, 12),
                    content=ft.Column(spacing=8, controls=format_controls),
                )
            ),
            ft.Divider(),
            _section_header(ft.Icons.HISTORY, "最近使用"),
            ft.Card(content=ft.Column(spacing=0, controls=recent_controls)),
            _section_header(ft.Icons.FILE_DOWNLOAD, "最近导出"),
            ft.Card(content=ft.Column(spacing=0, controls=export_controls)),
        ],
    )


# ── 局部组件 ─────────────────────────────────────────────


def _section_header(icon, label: str) -> ft.Row:
    return ft.Row(
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Icon(icon, size=18, color=COLORS["accent"]),
            ft.Text(label, size=FONT_SECTION, weight=ft.FontWeight.BOLD),
        ],
    )


def _rank_row(
    *,
    idx: int,
    name: str,
    score: int,
    max_score: int,
    description: str,
    on_click,
) -> ft.Control:
    ratio = score / max_score if max_score else 0
    rank_color = (
        COLORS["warning"] if idx == 1 else (COLORS["ink_muted"] if idx <= 3 else COLORS["ink_tertiary"])
    )
    title_row = ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=28,
                height=28,
                bgcolor=rank_color,
                border_radius=14,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    str(idx),
                    color=COLORS["on_primary"],
                    size=FONT_SMALL,
                    weight=ft.FontWeight.BOLD,
                ),
            ),
            ft.Column(
                tight=True,
                spacing=2,
                expand=True,
                controls=[
                    ft.Text(name, size=FONT_CARD_NAME, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        description or "",
                        size=FONT_CARD_DESC,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
            ),
            ft.Container(
                padding=ft.Padding(8, 4, 8, 4),
                bgcolor=COLORS["accent_soft"],
                border_radius=RADIUS_MD,
                content=ft.Text(
                    f"{score} 分",
                    size=FONT_SMALL,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["accent"],
                ),
            ),
        ],
    )
    bar = ft.ProgressBar(
        value=max(0.04, ratio),
        height=4,
        color=COLORS["accent"],
        bgcolor=COLORS["accent_soft"],
    )
    inner = ft.Column(spacing=6, controls=[title_row, bar])
    return ft.Container(
        padding=ft.Padding(8, 6, 8, 6),
        border_radius=8,
        ink=True,
        on_click=on_click,
        content=inner,
    )


def _format_row(fmt: str, count: int, ratio: float) -> ft.Control:
    label = fmt or "（未指定）"
    return ft.Column(
        spacing=4,
        controls=[
            ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(label, size=FONT_BODY, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Text(
                        f"{count} 次  ·  {ratio * 100:.0f}%",
                        size=FONT_META,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
            ),
            ft.ProgressBar(
                value=max(0.02, ratio),
                height=4,
                color=COLORS["accent"],
                bgcolor=COLORS["accent_soft"],
            ),
        ],
    )
