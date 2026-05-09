"""批量导出页：多选 Skill + 格式选择 + 目录选择 + 导出。"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from skills_manager.adapters import get_adapter, list_formats
from skills_manager.packager import pack_for_claude_code, pack_for_claude_desktop, pack_for_codex


def build_export_page(app) -> ft.Control:
    skills = app.skills

    if not skills:
        from ..components import EmptyState
        return EmptyState(
            on_install=lambda: app._show_install_dialog(),
            on_create=lambda: app.navigate("editor"),
        )

    # 初始化选中状态
    selected: dict[str, bool] = getattr(app, "_export_selected", {})
    if not selected:
        selected = {s.name: False for s in skills}
        app._export_selected = selected

    export_format = getattr(app, "_batch_export_format", "openai")
    pack_format = getattr(app, "_batch_pack_format", "")
    output_dir = getattr(app, "_batch_output_dir", "")

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
        path = await ft.FilePicker().get_directory_path()
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
                count += 1
            app.show_snack(f"已导出 {count} 个 Skill 到 {output_dir}")
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
            skill_dirs = [Path(app.store.get_skill_md_path(s.name)).parent for s in to_export]
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
        checkboxes.append(ft.Checkbox(
            label=f"{s.name} v{s.version}", value=selected.get(s.name, False),
            data=s.name, on_change=toggle_one,
        ))

    select_all = ft.Checkbox(
        label=f"全选 ({len(skills)} 个)",
        value=all(selected.values()) if selected else False,
        on_change=toggle_all,
    )

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            ft.Text("批量导出", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("选择要导出的 Skills 和目标格式", size=13),
            ft.Divider(),
            ft.Row([ft.Text("选择 Skills", size=16, weight=ft.FontWeight.BOLD), select_all]),
            ft.Column(controls=checkboxes, spacing=2),
            ft.Divider(),
            ft.Text("导出格式", size=16, weight=ft.FontWeight.BOLD),
            ft.Dropdown(options=[ft.DropdownOption(f) for f in list_formats()], value=export_format, width=200, on_select=on_format_change),
            ft.Divider(),
            ft.Text("打包格式", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("将 Skill 打包为平台特定格式", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
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
            ft.Row([
                ft.OutlinedButton("选择输出目录", icon=ft.Icons.FOLDER_OPEN, on_click=pick_dir),
                ft.Text(output_dir or "未选择目录", size=13, color=ft.Colors.ON_SURFACE_VARIANT, italic=True),
            ], spacing=8),
            ft.Row([
                ft.FilledButton("导出选中", icon=ft.Icons.FILE_DOWNLOAD, on_click=do_export),
                ft.FilledButton("打包选中", icon=ft.Icons.ARCHIVE, on_click=do_pack),
            ], spacing=8),
        ],
    )
