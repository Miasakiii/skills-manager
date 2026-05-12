"""Skill 详情页：参数表 + 导出预览 + 复制。"""

from __future__ import annotations

import flet as ft

from skills_manager.adapters import get_adapter, list_formats
from ..components import FONT_TITLE, FONT_SUBTITLE, FONT_SECTION


def build_detail_page(app) -> ft.Control:
    try:
        ir = app.store.get_skill_ir(app.selected_skill_name)
        # 记录使用历史
        app.store.add_usage(app.selected_skill_name, action="view")
    except Exception as e:
        app.selected_skill_name = None
        app.show_snack(f"加载 Skill 失败: {e}", error=True)
        from .browse import build_browse_page
        return build_browse_page(app)

    # 参数表（斑马条纹）
    param_rows = []
    for i, p in enumerate(ir.parameters):
        row_color = ft.Colors.SURFACE_CONTAINER_HIGHEST if i % 2 == 0 else ft.Colors.SURFACE
        param_rows.append(ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(p.name, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(p.type)),
                ft.DataCell(ft.Icon(ft.Icons.CHECK if p.required else ft.Icons.CLOSE, size=16,
                                    color=ft.Colors.GREEN if p.required else ft.Colors.GREY)),
                ft.DataCell(ft.Text(p.description, size=12)),
            ],
            color=row_color,
        ))

    param_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("参数")), ft.DataColumn(ft.Text("类型")),
            ft.DataColumn(ft.Text("必需")), ft.DataColumn(ft.Text("说明")),
        ],
        rows=param_rows,
        border=ft.Border(top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT), bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
    )

    # 导出预览
    def generate_preview() -> str:
        try:
            return get_adapter(app.export_format).export(ir)
        except Exception as e:
            return f"导出错误: {e}"

    preview_text = ft.Text(generate_preview(), font_family="monospace", size=12)

    def switch_format(e):
        app.export_format = e.control.value
        preview_text.value = generate_preview()
        app.page.update()

    def _show_uninstall():
        from ..dialogs import build_uninstall_dialog
        app._active_dialog = build_uninstall_dialog(app, ir.name)
        app.page.show_dialog(app._active_dialog)

    def do_update(_):
        """执行更新。"""
        try:
            result = app.store.update(ir.name)
            app._refresh_skills()
            app.show_snack(f"'{ir.name}' 已更新到 v{result.version}")
        except Exception as e:
            app.show_snack(f"更新失败: {e}", error=True)

    def do_translate(_):
        """翻译描述为中文。"""
        try:
            from skills_manager.translator import translate_skill_md
            content = app.store.get_skill_content(ir.name)
            translated = translate_skill_md(content, target_lang="zh-CN")
            if translated != content:
                app.store.get_skill_md_path(ir.name).write_text(translated, encoding="utf-8")
                app._refresh_skills()
                app.show_snack(f"'{ir.name}' 的描述已翻译为中文")
                app.selected_skill_name = ir.name
                app._update_ui()
            else:
                app.show_snack(f"'{ir.name}' 已经是中文或翻译服务不可用")
        except Exception as e:
            app.show_snack(f"翻译失败: {e}", error=True)

    # 检查是否可更新
    can_update, update_reason = app.store.can_update(ir.name)

    def copy_export(_):
        app.copy_to_clipboard(generate_preview())

    async def save_to_file(_):
        content = generate_preview()
        ext = get_adapter(app.export_format).file_extension
        path = f"{ir.name}{ext}"
        allowed = ["json", "py", "yaml", "yml"]
        save_path = await app.file_picker.save_file(
            file_name=path,
            allowed_extensions=allowed,
        )
        if save_path:
            try:
                from pathlib import Path
                Path(save_path).write_text(content, encoding="utf-8")
                app.show_snack(f"已保存到 {save_path}")
            except Exception as ex:
                app.show_snack(f"保存失败: {ex}", error=True)

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            ft.Row([
                ft.TextButton("返回", icon=ft.Icons.ARROW_BACK, on_click=lambda _: app.go_back()),
                ft.Row([
                    ft.TextButton("翻译", icon=ft.Icons.TRANSLATE, on_click=do_translate),
                    ft.TextButton(
                        "更新",
                        icon=ft.Icons.UPDATE,
                        on_click=do_update,
                        tooltip=update_reason,
                        disabled=not can_update,
                    ),
                    ft.TextButton("卸载", icon=ft.Icons.DELETE, on_click=lambda _: _show_uninstall()),
                ]),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                ft.Column(spacing=8, expand=True, controls=[
                    ft.Text(ir.name, size=FONT_TITLE, weight=ft.FontWeight.BOLD),
                    ft.Text(f"v{ir.version}  ·  {ir.category or '未分类'}", size=FONT_SUBTITLE, color=ft.Colors.ON_SURFACE_VARIANT),
                ]),
                ft.FilledButton("复制导出", icon=ft.Icons.CONTENT_COPY, on_click=copy_export),
                ft.OutlinedButton("保存文件", icon=ft.Icons.SAVE, on_click=save_to_file),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text(ir.description, size=FONT_SUBTITLE, italic=True),
            ft.Divider(),
            ft.Text(f"参数定义", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            param_table if ir.parameters else ft.Text("无参数", color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Divider(),
            ft.Text("导出预览", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
            ft.Dropdown(
                options=[ft.DropdownOption(f) for f in list_formats()],
                value=app.export_format,
                on_select=switch_format,
                width=200,
            ),
            ft.Container(
                content=preview_text,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                border_radius=8,
                padding=16,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
            ),
        ],
    )
