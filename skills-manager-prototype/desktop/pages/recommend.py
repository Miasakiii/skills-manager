"""场景推荐页面。"""

from __future__ import annotations

import flet as ft

from skills_manager.recommend import recommend_skills


def build_recommend_page(app) -> ft.Control:
    """构建场景推荐页面。"""
    skills = app.skills

    if not skills:
        from ..components import EmptyState
        return EmptyState(
            on_install=lambda: app._show_install_dialog(),
            on_create=lambda: app.navigate("editor"),
        )

    # 场景输入
    scenario_input = ft.TextField(
        label="场景描述",
        hint_text="描述你想要完成的任务，例如：我需要翻译一段技术文档到英文",
        multiline=True,
        min_lines=3,
        expand=True,
    )

    # 推荐结果容器
    results_column = ft.Column(
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    def do_recommend(_):
        """执行推荐。"""
        scenario = scenario_input.value.strip()
        if not scenario:
            app.show_snack("请输入场景描述", error=True)
            return

        # 构建 Skill 数据
        skill_data = []
        for s in skills:
            skill_data.append({
                "name": s.name,
                "description": s.description or "",
                "summary": s.summary or "",
                "tags": s.tags or [],
                "category": s.category or "",
            })

        # 执行推荐
        results = recommend_skills(scenario, skill_data)

        # 显示结果
        results_column.controls.clear()

        if not results:
            results_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "未找到匹配的 Skill，请尝试其他描述",
                        size=13,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    padding=16,
                )
            )
        else:
            results_column.controls.append(
                ft.Text(
                    f"找到 {len(results)} 个推荐 Skill",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                )
            )

            for rec in results:
                # 查找对应的 Skill 信息
                skill_info = None
                for s in skills:
                    if s.name == rec.skill_name:
                        skill_info = s
                        break

                if skill_info:
                    # 分数颜色
                    if rec.score >= 0.7:
                        score_color = ft.Colors.GREEN
                    elif rec.score >= 0.4:
                        score_color = ft.Colors.ORANGE
                    else:
                        score_color = ft.Colors.ON_SURFACE_VARIANT

                    results_column.controls.append(
                        ft.Card(
                            content=ft.Container(
                                padding=12,
                                content=ft.Row(
                                    spacing=12,
                                    controls=[
                                        ft.Column(
                                            spacing=4,
                                            expand=True,
                                            controls=[
                                                ft.Row([
                                                    ft.Text(
                                                        rec.skill_name,
                                                        size=16,
                                                        weight=ft.FontWeight.BOLD,
                                                    ),
                                                    ft.Container(
                                                        content=ft.Text(
                                                            f"{rec.score:.0%}",
                                                            size=12,
                                                            color=score_color,
                                                            weight=ft.FontWeight.BOLD,
                                                        ),
                                                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                                                        border_radius=4,
                                                        padding=ft.Padding(6, 2, 6, 2),
                                                    ),
                                                ]),
                                                ft.Text(
                                                    skill_info.description or skill_info.summary or "",
                                                    size=12,
                                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                                    max_lines=2,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                ),
                                                ft.Text(
                                                    f"推荐理由: {rec.reason}",
                                                    size=11,
                                                    color=ft.Colors.PRIMARY,
                                                ),
                                            ],
                                        ),
                                        ft.FilledButton(
                                            "查看详情",
                                            on_click=lambda _, name=rec.skill_name: app.show_detail(name),
                                        ),
                                    ],
                                ),
                            ),
                        )
                    )

        app._update_ui()

    return ft.Column(
        spacing=16,
        expand=True,
        controls=[
            ft.Text("场景推荐", size=22, weight=ft.FontWeight.BOLD),
            ft.Text(
                "描述你想要完成的任务，系统会推荐最合适的 Skill",
                size=13,
            ),
            ft.Divider(),
            scenario_input,
            ft.FilledButton(
                "推荐 Skill",
                icon=ft.Icons.AUTO_AWESOME,
                on_click=do_recommend,
            ),
            ft.Divider(),
            results_column,
        ],
    )
