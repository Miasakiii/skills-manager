"""MCP 客户端配置管理页面。

支持：
- 选择内置 profile（Claude Desktop / Claude Code / Cline）
- 添加自定义路径
- 查看 / 增删 mcpServers
- 一键把已安装 skill 注册为 MCP server
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from skills_manager.logging import get_logger
from skills_manager.mcp_config import (
    MCPConfigError,
    MCPConfigManager,
    MCPServer,
)

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

logger = get_logger(__name__)


def _profile_status_chip(prof) -> ft.Control:
    if prof.default_path is None:
        return ft.Container(
            content=ft.Text("不可用", size=FONT_SMALL, color=COLORS["on_primary"]),
            bgcolor=COLORS["ink_muted"],
            padding=ft.Padding(8, 2, 8, 2),
            border_radius=RADIUS_MD,
        )
    if prof.exists:
        return ft.Container(
            content=ft.Text("已存在", size=FONT_SMALL, color=COLORS["on_primary"]),
            bgcolor=COLORS["success"],
            padding=ft.Padding(8, 2, 8, 2),
            border_radius=RADIUS_MD,
        )
    return ft.Container(
        content=ft.Text("未创建", size=FONT_SMALL, color=COLORS["on_primary"]),
        bgcolor=COLORS["warning"],
        padding=ft.Padding(8, 2, 8, 2),
        border_radius=RADIUS_MD,
    )


def build_mcp_page(app) -> ft.Control:
    """构建 MCP 配置中心页面。"""

    # ── State 提升到 app 上，跨页保留 ──
    if app.mcp_manager is None:
        app.mcp_manager = MCPConfigManager(custom_paths=app.mcp_custom_paths)
    else:
        # 同步可能在其他地方更新的自定义路径
        app.mcp_manager._custom_paths = dict(app.mcp_custom_paths)
    mgr: MCPConfigManager = app.mcp_manager

    profiles = mgr.profiles()
    if not app.mcp_selected_profile:
        app.mcp_selected_profile = profiles[0].id if profiles else ""

    # 读取当前 profile 的 server 列表
    servers: list[MCPServer] = []
    load_error: str | None = None
    selected_path: Path | None = None
    try:
        if app.mcp_selected_profile:
            selected_path = mgr.resolve_path(app.mcp_selected_profile)
            servers = mgr.list_servers(app.mcp_selected_profile)
    except MCPConfigError as e:
        load_error = str(e)

    # ── 事件处理 ─────────────────────────────────────────────

    def reload():
        app._update_content()

    def on_select_profile(e):
        # Flet 0.84 的 Dropdown 通过 control 上的 value 取
        app.mcp_selected_profile = (
            getattr(e.control, "value", "") or ""
        )
        reload()

    def open_add_dialog(e=None):
        _show_add_server_dialog(app, on_saved=reload)

    def open_install_skill_dialog(e=None):
        _show_install_skill_dialog(app, on_saved=reload)

    def open_custom_path_dialog(e=None):
        _show_add_custom_profile_dialog(app, on_saved=reload)

    def make_remove_handler(name: str):
        def _handler(_):
            try:
                mgr.remove(app.mcp_selected_profile, name)
                app.show_snack(f"已移除 {name}")
            except MCPConfigError as exc:
                app.show_snack(f"移除失败：{exc}", error=True)
                return
            reload()

        return _handler

    def make_toggle_handler(server: MCPServer):
        def _handler(_):
            try:
                mgr.set_disabled(
                    app.mcp_selected_profile, server.name, not server.disabled
                )
                state = "禁用" if not server.disabled else "启用"
                app.show_snack(f"已{state} {server.name}")
            except MCPConfigError as exc:
                app.show_snack(f"操作失败：{exc}", error=True)
                return
            reload()

        return _handler

    # ── 顶部信息 ─────────────────────────────────────────────

    profile_dropdown = ft.Dropdown(
        value=app.mcp_selected_profile,
        on_select=on_select_profile,
        options=[ft.dropdown.Option(p.id, p.label) for p in profiles],
        width=260,
        dense=True,
        text_size=FONT_BODY,
    )

    selected_profile_obj = next(
        (p for p in profiles if p.id == app.mcp_selected_profile), None
    )

    header = ft.Row(
        spacing=12,
        controls=[
            ft.Text("MCP 配置中心", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.OutlinedButton(
                "自定义路径",
                icon=ft.Icons.FOLDER_OPEN,
                on_click=open_custom_path_dialog,
            ),
        ],
    )

    profile_card_controls: list[ft.Control] = [
        ft.Row(
            spacing=12,
            controls=[
                ft.Text("客户端", size=FONT_BODY),
                profile_dropdown,
                _profile_status_chip(selected_profile_obj)
                if selected_profile_obj
                else ft.Container(),
            ],
        ),
    ]
    if selected_profile_obj:
        profile_card_controls.append(
            ft.Text(
                selected_profile_obj.description,
                size=FONT_SMALL,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )
        if selected_profile_obj.default_path:
            profile_card_controls.append(
                ft.Text(
                    f"路径：{selected_profile_obj.default_path}",
                    size=FONT_SMALL,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    selectable=True,
                )
            )

    profile_card = ft.Container(
        padding=ft.Padding(16, 12, 16, 12),
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border_radius=10,
        content=ft.Column(spacing=8, controls=profile_card_controls),
    )

    # ── 操作按钮 ─────────────────────────────────────────────

    action_row = ft.Row(
        spacing=8,
        controls=[
            ft.FilledButton(
                "添加 MCP Server",
                icon=ft.Icons.ADD,
                on_click=open_add_dialog,
                disabled=load_error is not None,
            ),
            ft.OutlinedButton(
                "从已安装 Skill 注册",
                icon=ft.Icons.EXTENSION,
                on_click=open_install_skill_dialog,
                disabled=load_error is not None,
            ),
        ],
    )

    # ── server 列表 ──────────────────────────────────────────

    if load_error:
        body: ft.Control = ft.Container(
            padding=20,
            bgcolor=ft.Colors.ERROR_CONTAINER,
            border_radius=8,
            content=ft.Text(
                load_error, color=ft.Colors.ON_ERROR_CONTAINER, size=FONT_BODY
            ),
        )
    elif not servers:
        body = ft.Container(
            padding=ft.Padding(20, 32, 20, 32),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.INBOX, size=48, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Text(
                        "该客户端尚未配置任何 MCP Server",
                        size=FONT_SUBTITLE,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
            ),
        )
    else:
        rows: list[ft.Control] = []
        for s in servers:
            rows.append(_server_card(s, make_remove_handler, make_toggle_handler))
        body = ft.Column(spacing=8, controls=rows, scroll=ft.ScrollMode.AUTO)

    return ft.Column(
        spacing=16,
        expand=True,
        controls=[
            header,
            profile_card,
            action_row,
            ft.Divider(),
            ft.Container(content=body, expand=True),
        ],
    )


def _server_card(
    server: MCPServer,
    make_remove_handler,
    make_toggle_handler,
) -> ft.Control:
    state_chip = ft.Container(
        content=ft.Text(
            "已禁用" if server.disabled else "已启用",
            size=FONT_SMALL,
            color=COLORS["on_primary"],
        ),
        bgcolor=COLORS["ink_muted"] if server.disabled else COLORS["success"],
        padding=ft.Padding(8, 2, 8, 2),
        border_radius=RADIUS_MD,
    )

    args_text = " ".join(server.args) if server.args else "—"
    env_text = (
        ", ".join(f"{k}={v}" for k, v in server.env.items()) if server.env else "—"
    )

    return ft.Container(
        padding=ft.Padding(14, 12, 14, 12),
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border_radius=10,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.MEMORY, size=18, color=COLORS["accent"]),
                        ft.Text(
                            server.name,
                            size=FONT_CARD_NAME,
                            weight=ft.FontWeight.BOLD,
                        ),
                        state_chip,
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.TOGGLE_OFF
                            if server.disabled
                            else ft.Icons.TOGGLE_ON,
                            tooltip="启用" if server.disabled else "禁用",
                            on_click=make_toggle_handler(server),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.ERROR,
                            tooltip="移除",
                            on_click=make_remove_handler(server.name),
                        ),
                    ],
                ),
                ft.Text(
                    f"command  {server.command}",
                    size=FONT_CARD_DESC,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    selectable=True,
                ),
                ft.Text(
                    f"args     {args_text}",
                    size=FONT_CARD_DESC,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    selectable=True,
                ),
                ft.Text(
                    f"env      {env_text}",
                    size=FONT_META,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
        ),
    )


# ── 对话框 ─────────────────────────────────────────────────


def _show_add_server_dialog(app, on_saved) -> None:
    name_field = ft.TextField(label="名称", autofocus=True, dense=True)
    command_field = ft.TextField(label="Command", dense=True)
    args_field = ft.TextField(
        label="Args（每行一个）",
        multiline=True,
        min_lines=2,
        max_lines=5,
        dense=True,
    )
    env_field = ft.TextField(
        label="环境变量（每行 KEY=VALUE）",
        multiline=True,
        min_lines=2,
        max_lines=4,
        dense=True,
    )

    def on_save(_):
        name = name_field.value.strip()
        command = command_field.value.strip()
        if not name or not command:
            app.show_snack("名称和 Command 必填", error=True)
            return
        args = [
            line.strip()
            for line in (args_field.value or "").splitlines()
            if line.strip()
        ]
        env: dict[str, str] = {}
        for line in (env_field.value or "").splitlines():
            line = line.strip()
            if not line:
                continue
            if "=" not in line:
                app.show_snack(f"环境变量格式错误：{line}", error=True)
                return
            k, v = line.split("=", 1)
            env[k.strip()] = v
        server = MCPServer(name=name, command=command, args=args, env=env)
        try:
            app.mcp_manager.add_or_update(app.mcp_selected_profile, server)
        except MCPConfigError as exc:
            app.show_snack(f"保存失败：{exc}", error=True)
            return
        app._close_active_dialog()
        app.show_snack(f"已写入 {name}")
        on_saved()

    dialog = ft.AlertDialog(
        title=ft.Text("添加 MCP Server", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            width=480,
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[name_field, command_field, args_field, env_field],
            ),
        ),
        actions=[
            ft.TextButton("取消", on_click=lambda e: app._close_active_dialog()),
            ft.FilledButton("保存", on_click=on_save),
        ],
    )
    app._active_dialog = dialog
    app.page.show_dialog(dialog)


def _show_install_skill_dialog(app, on_saved) -> None:
    if not app.skills:
        app.show_snack("还没有安装任何 Skill，先去浏览页添加一个吧", error=True)
        return

    skill_dropdown = ft.Dropdown(
        label="选择 Skill",
        options=[ft.dropdown.Option(s.name, s.name) for s in app.skills],
        dense=True,
        value=app.skills[0].name,
    )
    entry_field = ft.TextField(label="入口脚本", value="server.py", dense=True)
    python_field = ft.TextField(
        label="Python 解释器（留空使用当前）",
        hint_text="留空使用 sys.executable",
        dense=True,
    )

    def on_save(_):
        skill_name = skill_dropdown.value
        if not skill_name:
            app.show_snack("请选择 Skill", error=True)
            return
        try:
            skill = app.store.get(skill_name)
        except Exception as exc:
            app.show_snack(f"找不到 Skill：{exc}", error=True)
            return
        try:
            server = app.mcp_manager.install_skill_to(
                app.mcp_selected_profile,
                skill_name=skill.name,
                skill_path=Path(skill.path),
                python_executable=python_field.value.strip() or None,
                entry=entry_field.value.strip() or "server.py",
            )
        except MCPConfigError as exc:
            app.show_snack(f"写入失败：{exc}", error=True)
            return
        app._close_active_dialog()
        app.show_snack(f"已把 {server.name} 注册为 MCP Server")
        on_saved()

    dialog = ft.AlertDialog(
        title=ft.Text(
            "从已安装 Skill 注册", size=FONT_SECTION, weight=ft.FontWeight.BOLD
        ),
        content=ft.Container(
            width=440,
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[skill_dropdown, entry_field, python_field],
            ),
        ),
        actions=[
            ft.TextButton("取消", on_click=lambda e: app._close_active_dialog()),
            ft.FilledButton("写入", on_click=on_save),
        ],
    )
    app._active_dialog = dialog
    app.page.show_dialog(dialog)


def _show_add_custom_profile_dialog(app, on_saved) -> None:
    label_field = ft.TextField(label="显示名称", dense=True, autofocus=True)
    path_field = ft.TextField(
        label="JSON 文件路径",
        hint_text="如 D:/custom/mcpServers.json",
        dense=True,
    )

    def on_save(_):
        label = (label_field.value or "").strip()
        path_text = (path_field.value or "").strip()
        if not label or not path_text:
            app.show_snack("请填写名称和路径", error=True)
            return
        path = Path(path_text)
        try:
            prof = app.mcp_manager.add_custom_profile(label, path)
        except MCPConfigError as exc:
            app.show_snack(f"添加失败：{exc}", error=True)
            return
        # 持久化到 app 状态
        app.mcp_custom_paths[label] = path
        app.mcp_selected_profile = prof.id
        app._close_active_dialog()
        app.show_snack(f"已添加自定义 profile：{label}")
        on_saved()

    dialog = ft.AlertDialog(
        title=ft.Text("添加自定义路径", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            width=440,
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[label_field, path_field],
            ),
        ),
        actions=[
            ft.TextButton("取消", on_click=lambda e: app._close_active_dialog()),
            ft.FilledButton("保存", on_click=on_save),
        ],
    )
    app._active_dialog = dialog
    app.page.show_dialog(dialog)
