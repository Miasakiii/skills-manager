"""Profile 管理页面。"""

from __future__ import annotations

import flet as ft

from ..components import FONT_TITLE, FONT_SUBTITLE, FONT_CARD_NAME, FONT_CARD_DESC, FONT_SECTION


def build_profiles_page(app) -> ft.Control:
    """构建 Profile 管理页面。"""
    profiles = app.store.get_profiles()
    skills = app.skills

    # 当前编辑的 Profile
    editing_profile = getattr(app, "_editing_profile", None)

    # Profile 列表容器
    profiles_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)

    # 编辑区域容器
    edit_area = ft.Container(expand=True)

    def _rebuild_profiles_list():
        """重建 Profile 列表。"""
        profiles_list.controls.clear()

        if not profiles:
            profiles_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "暂无 Profile，点击「新建」创建",
                        size=FONT_SUBTITLE,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    padding=16,
                )
            )
            return

        for p in profiles:
            skill_count = len(p.get("skills", []))

            def make_on_click(name=p["name"]):
                return lambda _: edit_profile(name)

            def make_on_delete(name=p["name"]):
                return lambda _: delete_profile(name)

            profiles_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Row(
                            spacing=12,
                            controls=[
                                ft.Icon(ft.Icons.PERSON, size=24),
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(
                                            p["name"],
                                            size=FONT_CARD_NAME,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            p.get("description", "") or f"{skill_count} 个 Skill",
                                            size=FONT_CARD_DESC,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                    ],
                                ),
                                ft.IconButton(
                                    ft.Icons.EDIT,
                                    on_click=make_on_click(),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    on_click=make_on_delete(),
                                ),
                            ],
                        ),
                    ),
                )
            )

    def _rebuild_edit_area():
        """重建编辑区域。"""
        if not editing_profile:
            edit_area.content = ft.Container(
                content=ft.Text(
                    "选择或创建 Profile 进行编辑",
                    size=FONT_SUBTITLE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                alignment=ft.alignment.Alignment(0, 0),
                padding=32,
            )
            return

        profile = None
        for p in profiles:
            if p["name"] == editing_profile:
                profile = p
                break

        if not profile:
            edit_area.content = ft.Text("Profile 不存在")
            return

        profile_skills = profile.get("skills", [])

        # Skill 多选列表
        skill_checkboxes = []
        for s in skills:
            is_in_profile = s.name in profile_skills

            def make_on_change(name=s.name, current=is_in_profile):
                def on_change(e):
                    if e.control.value:
                        app.store.add_skill_to_profile(editing_profile, name)
                    else:
                        app.store.remove_skill_from_profile(editing_profile, name)
                    _rebuild_edit_area()
                    app._update_ui()
                return on_change

            skill_checkboxes.append(
                ft.Checkbox(
                    label=f"{s.name} v{s.version}",
                    value=is_in_profile,
                    on_change=make_on_change(),
                )
            )

        edit_area.content = ft.Column(
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.Text(
                        f"编辑 Profile: {editing_profile}",
                        size=FONT_TITLE,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(expand=True),
                    ft.TextButton(
                        "关闭",
                        on_click=lambda _: close_edit(),
                    ),
                ]),
                ft.Text(
                    profile.get("description", ""),
                    size=FONT_SUBTITLE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Divider(),
                ft.Text("包含的 Skill", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "勾选要包含在此 Profile 中的 Skill",
                    size=FONT_SUBTITLE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Column(controls=skill_checkboxes, spacing=4),
                ft.Divider(),
                ft.Text(
                    f"已选择 {len(profile_skills)} 个 Skill",
                    size=FONT_SUBTITLE,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
        )

    def edit_profile(name: str):
        """编辑 Profile。"""
        app._editing_profile = name
        _rebuild_edit_area()
        app._update_ui()

    def close_edit():
        """关闭编辑。"""
        app._editing_profile = None
        _rebuild_edit_area()
        app._update_ui()

    def delete_profile(name: str):
        """删除 Profile。"""
        app.store.delete_profile(name)
        if app._editing_profile == name:
            app._editing_profile = None
        _rebuild_profiles_list()
        _rebuild_edit_area()
        app._update_ui()
        app.show_snack(f"已删除 Profile: {name}")

    def create_new_profile(_):
        """创建新 Profile。"""
        # 显示创建对话框
        name_input = ft.TextField(label="Profile 名称", autofocus=True)
        desc_input = ft.TextField(label="描述（可选）")

        def do_create(_):
            name = name_input.value.strip()
            if not name:
                app.show_snack("请输入 Profile 名称", error=True)
                return
            try:
                app.store.create_profile(
                    name=name,
                    description=desc_input.value.strip(),
                )
                app._close_active_dialog()
                _rebuild_profiles_list()
                app._update_ui()
                app.show_snack(f"已创建 Profile: {name}")
            except Exception as e:
                app.show_snack(f"创建失败: {e}", error=True)

        dialog = ft.AlertDialog(
            title=ft.Text("新建 Profile"),
            content=ft.Column(
                spacing=12,
                tight=True,
                controls=[name_input, desc_input],
            ),
            actions=[
                ft.TextButton(
                    "取消",
                    on_click=lambda _: app._close_active_dialog(),
                ),
                ft.FilledButton("创建", on_click=do_create),
            ],
        )
        app._active_dialog = dialog
        app.page.show_dialog(dialog)

    # 初始化
    _rebuild_profiles_list()
    _rebuild_edit_area()

    return ft.Row(
        spacing=16,
        expand=True,
        controls=[
            # 左侧：Profile 列表
            ft.Container(
                width=300,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Row([
                            ft.Text(
                                "Profile 管理",
                                size=FONT_TITLE,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Container(expand=True),
                            ft.FilledButton(
                                "新建",
                                icon=ft.Icons.ADD,
                                on_click=create_new_profile,
                            ),
                        ]),
                        ft.Text(
                            "管理 Agent 的 Skill 组合配置",
                            size=FONT_SUBTITLE,
                        ),
                        ft.Divider(),
                        profiles_list,
                    ],
                ),
            ),
            ft.VerticalDivider(),
            # 右侧：编辑区域
            edit_area,
        ],
    )
