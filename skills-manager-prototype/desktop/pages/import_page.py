"""批量导入页面。"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from ..components import FONT_TITLE, FONT_SUBTITLE


def build_import_page(app) -> ft.Control:
    """构建批量导入页面。"""
    scan_path = app._import_scan_path
    results = app._import_results
    selected = app._import_selected

    # 扫描路径显示
    path_text = ft.Text(
        scan_path or "请选择要扫描的目录",
        size=FONT_SUBTITLE,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )

    # 结果列表容器
    results_column = ft.Column(
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # 状态栏
    status_text = ft.Text("", size=12)

    def update_results_list():
        """更新结果列表显示。"""
        results_column.controls.clear()

        if not results:
            results_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "点击「扫描」查找目录中的 Skill",
                        size=FONT_SUBTITLE,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    alignment=ft.alignment.Alignment(0, 0),
                    padding=32,
                )
            )
            return

        # 全选复选框
        non_installed = [r for r in results if not r["installed"]]
        all_selected = all(
            selected.get(r["name"], False) for r in non_installed
        )

        def toggle_all(e):
            for r in results:
                if not r["installed"]:
                    selected[r["name"]] = e.control.value
            app._import_selected = selected
            update_results_list()
            app._update_ui()

        results_column.controls.append(
            ft.Checkbox(
                label=f"全选 ({len(non_installed)} 个可导入)",
                value=all_selected,
                on_change=toggle_all,
            )
        )
        results_column.controls.append(ft.Divider())

        # 单个 Skill 复选框
        for r in results:
            name = r["name"]
            is_installed = r["installed"]

            def toggle_one(e, n=name):
                selected[n] = e.control.value
                app._import_selected = selected
                update_status()

            label = f"{name}"
            if r["version"]:
                label += f" v{r['version']}"
            if r["description"]:
                desc = r["description"]
                if len(desc) > 40:
                    desc = desc[:37] + "..."
                label += f" — {desc}"

            cb = ft.Checkbox(
                label=label,
                value=selected.get(name, False),
                disabled=is_installed,
                data=name,
                on_change=toggle_one,
            )

            if is_installed:
                row = ft.Row(
                    [
                        cb,
                        ft.Container(
                            content=ft.Text(
                                "[已安装]",
                                size=11,
                                color=ft.Colors.PRIMARY,
                            ),
                            alignment=ft.alignment.Alignment(1, 0),
                            expand=True,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
                results_column.controls.append(row)
            else:
                results_column.controls.append(cb)

    def update_status():
        """更新状态栏。"""
        count = sum(
            1 for r in results
            if selected.get(r["name"], False) and not r["installed"]
        )
        if results:
            status_text.value = f"共 {len(results)} 个 Skill，已选 {count} 个"
        else:
            status_text.value = ""

    async def pick_dir(_):
        """选择扫描目录。"""
        path = await app.file_picker.get_directory_path()
        if path:
            app._import_scan_path = path
            path_text.value = path
            # 清空之前的结果
            app._import_results = []
            app._import_selected = {}
            results_column.controls.clear()
            update_status()
            app._update_ui()

    def scan_dir(_):
        """扫描目录。"""
        scan_path = app._import_scan_path
        if not scan_path:
            app.show_snack("请先选择目录", error=True)
            return

        root = Path(scan_path)
        if not root.is_dir():
            app.show_snack("目录不存在", error=True)
            return

        try:
            results = app.store.scan_directory_with_info(root)
            app._import_results = results
            # 初始化选中状态：未安装的默认选中
            selected = {}
            for r in results:
                selected[r["name"]] = not r["installed"]
            app._import_selected = selected
            update_results_list()
            update_status()
            app._update_ui()

            if not results:
                app.show_snack("未找到任何 Skill")
            else:
                count = sum(1 for r in results if not r["installed"])
                app.show_snack(f"发现 {len(results)} 个 Skill，{count} 个可导入")
        except Exception as e:
            app.show_snack(f"扫描失败: {e}", error=True)

    def import_selected(_):
        """导入选中的 Skill。"""
        results = app._import_results
        selected = app._import_selected

        to_import = [
            r for r in results
            if selected.get(r["name"], False) and not r["installed"]
        ]

        if not to_import:
            app.show_snack("未选择任何 Skill", error=True)
            return

        installed = []
        failed = []
        for r in to_import:
            try:
                app.store.install(r["path"], force=True)
                installed.append(r["name"])
            except Exception as e:
                failed.append((r["name"], str(e)))

        # 刷新 Skill 列表
        app._refresh_skills()

        # 显示结果
        if installed and not failed:
            app.show_snack(f"成功导入 {len(installed)} 个 Skill")
        elif installed and failed:
            names = ", ".join(n for n, _ in failed)
            app.show_snack(
                f"导入 {len(installed)} 个，失败: {names}",
                error=True,
            )
        else:
            names = ", ".join(n for n, _ in failed)
            app.show_snack(f"导入失败: {names}", error=True)

        # 重新扫描以更新状态
        scan_path = app._import_scan_path
        if scan_path:
            results = app.store.scan_directory_with_info(Path(scan_path))
            app._import_results = results
            selected = {r["name"]: not r["installed"] for r in results}
            app._import_selected = selected
            update_results_list()
            update_status()
            app._update_ui()

    # 初始化显示
    if results:
        update_results_list()
        update_status()

    return ft.Column(
        spacing=12,
        expand=True,
        controls=[
            ft.Text("批量导入", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
            ft.Text("从目录扫描并批量导入多个 Skill", size=FONT_SUBTITLE),
            ft.Divider(),
            # 目录选择行
            ft.Row(
                spacing=8,
                controls=[
                    ft.ElevatedButton(
                        "选择目录",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=pick_dir,
                    ),
                    ft.Container(
                        content=path_text,
                        expand=True,
                    ),
                    ft.ElevatedButton(
                        "扫描",
                        icon=ft.Icons.SEARCH,
                        on_click=scan_dir,
                    ),
                ],
            ),
            ft.Divider(),
            # 结果列表
            ft.Container(
                content=results_column,
                expand=True,
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                border_radius=8,
                padding=8,
            ),
            # 底部状态栏和操作按钮
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    status_text,
                    ft.FilledButton(
                        "导入选中",
                        icon=ft.Icons.DOWNLOAD,
                        on_click=import_selected,
                    ),
                ],
            ),
        ],
    )
