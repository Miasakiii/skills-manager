"""批量导出页：多选 Skill + 格式选择 + 目录选择 + 导出。"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from skills_manager.adapters import get_adapter, list_formats
from skills_manager.packager import (
    pack_for_claude_code,
    pack_for_claude_desktop,
    pack_for_codex,
)
from ..components import FONT_TITLE, FONT_SUBTITLE, FONT_SECTION, FONT_META, FONT_TAG
from ..theme import COLORS, RADIUS_MD


def build_export_page(app) -> ft.Control:
    skills = app.skills

    if not skills:
        from ..components import EmptyState

        return EmptyState(
            on_install=lambda: app._show_install_dialog(),
            on_create=lambda: app.navigate("editor"),
        )

    # 初始化选中状态
    selected = app._export_selected
    if not selected:
        selected = {s.name: False for s in skills}
        app._export_selected = selected

    export_format = app._batch_export_format
    pack_format = app._batch_pack_format
    output_dir = app._batch_output_dir

    def toggle_all(e):
        check_all = e.control.value
        for s in skills:
            selected[s.name] = check_all
        app._update_ui()

    def toggle_one(e):
        selected[e.control.data] = e.control.value
        app._export_selected = selected

    def on_format_change(e):
        app._batch_export_format = e.control.value

    def on_pack_format_change(e):
        app._batch_pack_format = e.control.value

    async def pick_dir(_):
        path = await app.file_picker.get_directory_path()
        if path:
            app._batch_output_dir = path
            app._update_ui()

    async def do_export(_):
        to_export = [s for s in skills if selected.get(s.name)]
        if not to_export:
            app.show_snack("请至少选择一个 Skill", error=True)
            return
        if not output_dir:
            app.show_snack("请先选择输出目录", error=True)
            return

        try:
            adapter = get_adapter(export_format)
            dest = Path(output_dir) / f"skills-{export_format}"
            dest.mkdir(parents=True, exist_ok=True)
            count = 0
            for s in to_export:
                ir = app.store.get_skill_ir(s.name)
                content = adapter.export(ir)
                out_path = dest / f"{ir.name}{adapter.file_extension}"
                out_path.write_text(content, encoding="utf-8")
                # 记录导出历史
                app.store.add_export_history(
                    skill_name=s.name,
                    format_name=export_format,
                    output_path=str(out_path),
                )
                count += 1
            app.show_snack(f"已导出 {count} 个 Skill 到 {output_dir}")
            _rebuild_history()
            app._update_ui()
        except Exception as e:
            app.show_snack(f"导出失败: {e}", error=True)

    async def do_pack(_):
        to_export = [s for s in skills if selected.get(s.name)]
        if not to_export:
            app.show_snack("请至少选择一个 Skill", error=True)
            return
        if not output_dir:
            app.show_snack("请先选择输出目录", error=True)
            return
        if not pack_format:
            app.show_snack("请先选择打包格式", error=True)
            return

        try:
            skill_dirs = [
                Path(app.store.get_skill_md_path(s.name)).parent for s in to_export
            ]
            dest = Path(output_dir)

            if pack_format == "claude-desktop":
                result = pack_for_claude_desktop(skill_dirs, dest)
            elif pack_format == "codex":
                result = pack_for_codex(skill_dirs, dest)
            elif pack_format == "claude-code":
                result = pack_for_claude_code(skill_dirs, dest)
            else:
                app.show_snack(f"未知打包格式: {pack_format}", error=True)
                return

            app.show_snack(f"已打包 {len(to_export)} 个 Skill 到 {result}")
        except Exception as e:
            app.show_snack(f"打包失败: {e}", error=True)

    checkboxes = []
    for s in skills:
        checkboxes.append(
            ft.Checkbox(
                label=f"{s.name} v{s.version}",
                value=selected.get(s.name, False),
                data=s.name,
                on_change=toggle_one,
            )
        )

    select_all = ft.Checkbox(
        label=f"全选 ({len(skills)} 个)",
        value=all(selected.values()) if selected else False,
        on_change=toggle_all,
    )

    # 导出历史记录容器
    history_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)

    def _rebuild_history():
        """重建导出历史列表。"""
        history = app.store.get_export_history()
        history_column.controls.clear()

        if not history:
            history_column.controls.append(
                ft.Text(
                    "暂无导出记录",
                    size=FONT_META,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                )
            )
            return

        # 显示最近 20 条
        for entry in reversed(history[-20:]):
            time_str = entry.get("exported_at", "")[:19].replace("T", " ")
            history_column.controls.append(
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.FILE_DOWNLOAD, size=14),
                        ft.Text(
                            f"{entry['skill_name']} → {entry['format']}",
                            size=FONT_META,
                            expand=True,
                        ),
                        ft.Text(
                            time_str,
                            size=FONT_TAG,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                )
            )

    def clear_history(_):
        """清空导出历史。"""
        app.store.clear_export_history()
        _rebuild_history()
        app._update_ui()
        app.show_snack("已清空导出历史")

    _rebuild_history()

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.FILE_DOWNLOAD, color=COLORS["on_primary"], size=18
                        ),
                        bgcolor=COLORS["accent"],
                        border_radius=RADIUS_MD,
                        padding=ft.Padding(6, 6, 6, 6),
                    ),
                    ft.Text("批量导出", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            ft.Text(
                "选择要导出的 Skills 和目标格式",
                size=FONT_SUBTITLE,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Divider(),
            ft.Row(
                [
                    ft.Text(
                        "选择 Skills", size=FONT_SECTION, weight=ft.FontWeight.BOLD
                    ),
                    select_all,
                ]
            ),
            ft.Container(
                content=ft.Column(controls=checkboxes, spacing=4),
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                border_radius=12,
                padding=16,
                border=ft.Border(
                    top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    left=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                    bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                ),
            ),
            ft.Divider(),
            ft.Text("导出格式", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            ft.Dropdown(
                options=[ft.DropdownOption(f) for f in list_formats()],
                value=export_format,
                width=200,
                on_select=on_format_change,
            ),
            ft.Divider(),
            ft.Text("打包格式", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            ft.Text(
                "将 Skill 打包为平台特定格式",
                size=FONT_META,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Dropdown(
                options=[
                    ft.DropdownOption("", text="不打包"),
                    ft.DropdownOption("claude-desktop", text="Claude Desktop"),
                    ft.DropdownOption("codex", text="Codex"),
                    ft.DropdownOption("claude-code", text="Claude Code"),
                ],
                value=pack_format,
                width=200,
                on_select=on_pack_format_change,
            ),
            ft.Divider(),
            ft.Row(
                [
                    ft.OutlinedButton(
                        "选择输出目录", icon=ft.Icons.FOLDER_OPEN, on_click=pick_dir
                    ),
                    ft.Text(
                        output_dir or "未选择目录",
                        size=FONT_SUBTITLE,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                ],
                spacing=8,
            ),
            ft.Row(
                [
                    ft.FilledButton(
                        "导出选中",
                        icon=ft.Icons.FILE_DOWNLOAD,
                        on_click=do_export,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10)
                        ),
                    ),
                    ft.FilledButton(
                        "打包选中",
                        icon=ft.Icons.ARCHIVE,
                        on_click=do_pack,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10)
                        ),
                    ),
                ],
                spacing=8,
            ),
            ft.Divider(),
            ft.Row(
                [
                    ft.Text("导出历史", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.TextButton(
                        "清空历史",
                        icon=ft.Icons.DELETE_OUTLINE,
                        on_click=clear_history,
                    ),
                ]
            ),
            history_column,
        ],
    )
