"""CLI 命令行入口。"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .adapters import get_adapter, list_formats
from .packager import pack as pack_skill
from .parser import parse_skill_md
from .store import Store, StoreError

app = typer.Typer(
    name="skills",
    help="AI Skill 格式转换与管理工具",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"skills-manager {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True
    ),
) -> None:
    """AI Skill 格式转换与管理工具。"""


# ── 导出 ──────────────────────────────────────────────────


@app.command()
def export(
    name: str = typer.Argument(None, help="Skill 名称（不指定则导出当前目录）"),
    format: str = typer.Option("openai", "--format", "-f", help="目标格式"),
    output: str = typer.Option(None, "--output", "-o", help="输出路径"),
    all: bool = typer.Option(False, "--all", "-a", help="导出所有已安装 Skill"),
    current_dir: bool = typer.Option(
        False, "--current-dir", "-d", help="从当前目录的 SKILL.md 导出"
    ),
) -> None:
    """导出 Skill 为目标平台格式。"""
    try:
        adapter = get_adapter(format)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if current_dir or (name is None and not all):
        # 从当前目录导出
        skill_md = Path("SKILL.md")
        if not skill_md.exists():
            console.print("[red]Error:[/red] No SKILL.md found in current directory")
            raise typer.Exit(1)
        ir = parse_skill_md(skill_md)
        content = adapter.export(ir)
        _output_result(content, output, ir.name, adapter.file_extension)
        return

    store = Store()

    if all:
        skills = store.list_all()
        if not skills:
            console.print("[yellow]No installed skills found.[/yellow]")
            return
        for skill in skills:
            ir = store.get_skill_ir(skill.name)
            content = adapter.export(ir)
            if output:
                out_dir = Path(output)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{skill.name}{adapter.file_extension}"
            else:
                out_path = Path(f"{skill.name}{adapter.file_extension}")
            out_path.write_text(content, encoding="utf-8")
            console.print(f"[green]OK[/green] {skill.name} -> {out_path}")
    else:
        if not name:
            console.print(
                "[red]Error:[/red] Please specify a skill name or use --current-dir"
            )
            raise typer.Exit(1)
        try:
            ir = store.get_skill_ir(name)
        except StoreError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        content = adapter.export(ir)
        _output_result(content, output, name, adapter.file_extension)


def _output_result(content: str, output: str | None, name: str, ext: str) -> None:
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"[green]OK[/green] Exported to {out_path}")
    else:
        console.print(content)


# ── 安装 ──────────────────────────────────────────────────


@app.command()
def install(
    source: str = typer.Argument(..., help="Skill 目录路径或 .skill 包文件"),
    name: str = typer.Option(None, "--name", "-n", help="自定义安装名"),
    force: bool = typer.Option(False, "--force", help="覆盖已有"),
) -> None:
    """安装 Skill。"""
    store = Store()
    source_path = Path(source)

    try:
        if source_path.suffix == ".skill":
            result = store.install_from_package(source_path)
        else:
            result = store.install(source_path, name=name, force=force)
        console.print(f"[green]OK[/green] Installed {result.name} v{result.version}")
    except (StoreError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("install-url")
def install_url(
    url: str = typer.Argument(..., help="URL 地址（.skill 包或 GitHub 仓库）"),
) -> None:
    """从 URL 安装 Skill。"""
    store = Store()

    try:
        result = store.install_from_url(url)
        console.print(f"[green]OK[/green] Installed {result.name} v{result.version}")
    except StoreError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ── 卸载 ──────────────────────────────────────────────────


@app.command()
def uninstall(
    names: list[str] = typer.Argument(..., help="一个或多个 Skill 名称"),
) -> None:
    """卸载 Skill（支持批量）。"""
    store = Store()
    if len(names) == 1:
        try:
            store.uninstall(names[0])
            console.print(f"[green]OK[/green] Uninstalled {names[0]}")
        except StoreError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        return

    succeeded, failed = store.uninstall_many(names)
    for name in succeeded:
        console.print(f"[green]OK[/green] Uninstalled {name}")
    for name, msg in failed:
        console.print(f"[red]Fail[/red] {name}: {msg}")
    if failed:
        raise typer.Exit(1)


# ── 列表 ──────────────────────────────────────────────────


@app.command("list")
def list_skills(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
) -> None:
    """列出所有已安装 Skill。"""
    store = Store()
    skills = store.list_all()

    if not skills:
        console.print(
            "[yellow]No installed skills. Use 'skills install' to add.[/yellow]"
        )
        return

    table = Table(title=f"Installed Skills ({len(skills)})")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Category", style="magenta")
    table.add_column("Description")

    for s in skills:
        desc = s.summary or s.description or ""
        if not verbose and len(desc) > 60:
            desc = desc[:57] + "..."
        table.add_row(s.name, s.version, s.category or "", desc)

    console.print(table)


# ── 详情 ──────────────────────────────────────────────────


@app.command()
def info(
    name: str = typer.Argument(..., help="Skill 名称"),
) -> None:
    """查看 Skill 详细信息。"""
    store = Store()
    try:
        skill = store.get(name)
        ir = store.get_skill_ir(name)
    except StoreError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"[bold cyan]{ir.name}[/bold cyan] v{ir.version}")
    console.print(f"  {ir.description}")
    if ir.summary:
        console.print(f"  [dim]{ir.summary}[/dim]")
    console.print()

    if ir.tags:
        console.print(f"  Tags: {', '.join(ir.tags)}")
    if ir.category:
        console.print(f"  Category: {ir.category}")
    if ir.author:
        console.print(f"  Author: {ir.author}")
    console.print()

    if ir.parameters:
        console.print("  [bold]Parameters:[/bold]")
        param_table = Table(show_header=True, box=None, padding=(0, 2))
        param_table.add_column("Name", style="cyan")
        param_table.add_column("Type")
        param_table.add_column("Required")
        param_table.add_column("Description")
        for p in ir.parameters:
            req = "是" if p.required else "否"
            param_table.add_row(p.name, p.type, req, p.description)
        console.print(param_table)

    console.print(f"\n  [dim]Installed: {skill.installed_at}[/dim]")
    console.print(f"  [dim]Source: {skill.source}[/dim]")
    console.print(f"  [dim]Path: {skill.path}[/dim]")


# ── 搜索 ──────────────────────────────────────────────────


@app.command()
def search(
    query: str = typer.Argument(..., help="搜索关键词"),
    category: str = typer.Option(None, "--category", "-c", help="按分类筛选"),
    tag: str = typer.Option(None, "--tag", "-t", help="按标签筛选"),
) -> None:
    """搜索已安装的 Skills。"""
    store = Store()
    results = store.search(query, tag=tag, category=category)

    if not results:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        return

    console.print(f"Found {len(results)} result(s):\n")
    for s in results:
        console.print(f"  [cyan]{s.name}[/cyan] {s.version}  {s.description}")


# ── 打包 ──────────────────────────────────────────────────


@app.command()
def pack(
    dir: str = typer.Argument(..., help="Skill 目录路径"),
    output: str = typer.Option(None, "--output", "-o", help="输出目录"),
) -> None:
    """将 Skill 目录打包为 .skill 文件。"""
    source = Path(dir)
    output_dir = Path(output) if output else None

    try:
        result = pack_skill(source, output_dir)
        console.print(f"[green]OK[/green] Packed to {result}")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ── 版本管理 ──────────────────────────────────────────────


@app.command()
def upgrade(
    name: str = typer.Argument(..., help="Skill 名称"),
    source: str = typer.Argument(..., help="新版本的 Skill 目录路径"),
) -> None:
    """升级 Skill 到新版本。"""
    store = Store()
    source_path = Path(source)

    try:
        result = store.upgrade(name, source_path)
        console.print(f"[green]OK[/green] Upgraded {name} to v{result.version}")
    except (StoreError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def rollback(
    name: str = typer.Argument(..., help="Skill 名称"),
    version: str = typer.Argument(None, help="要回滚的版本号（默认上一个版本）"),
) -> None:
    """回滚 Skill 到指定版本。"""
    store = Store()

    try:
        result = store.rollback(name, version)
        console.print(f"[green]OK[/green] Rolled back {name} to v{result.version}")
    except StoreError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("check-updates")
def check_updates() -> None:
    """检查所有已安装 Skill 是否有新版本。"""
    store = Store()
    entries = store.check_outdated()
    if not entries:
        console.print("[yellow]No installed skills.[/yellow]")
        return

    table = Table(title="Skill Update Check")
    table.add_column("Name", style="cyan")
    table.add_column("Current")
    table.add_column("Latest")
    table.add_column("Status")
    table.add_column("Reason", style="dim")
    updatable_count = 0
    for e in entries:
        cur = e.get("current_version") or "?"
        latest = e.get("latest_version") or "—"
        if e.get("updatable"):
            status = "[green]updatable[/green]"
            updatable_count += 1
        else:
            status = "[dim]up to date[/dim]"
        table.add_row(e["name"], cur, latest, status, e.get("reason", ""))
    console.print(table)
    console.print(f"\n[bold]{len(entries)} skills, {updatable_count} updatable[/bold]")


@app.command("update-all")
def update_all_cmd(
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认"),
) -> None:
    """对所有可更新 Skill 执行更新。"""
    store = Store()
    entries = [e for e in store.check_outdated() if e.get("updatable")]
    if not entries:
        console.print("[yellow]No updatable skills[/yellow]")
        return

    console.print(f"About to update {len(entries)} skill(s):")
    for e in entries:
        console.print(f"  - {e['name']}  ({e.get('reason', '')})")
    if not yes:
        confirm = typer.confirm("Continue?", default=True)
        if not confirm:
            raise typer.Exit(0)

    succeeded, failed = store.update_all()
    for name in succeeded:
        console.print(f"[green]OK[/green] Updated {name}")
    for name, msg in failed:
        console.print(f"[red]Fail[/red] {name}: {msg}")
    if failed:
        raise typer.Exit(1)


@app.command("history")
def version_history(
    name: str = typer.Argument(..., help="Skill 名称"),
) -> None:
    """查看 Skill 的版本历史。"""
    store = Store()

    try:
        history = store.get_version_history(name)
        if not history:
            console.print(f"[yellow]No version history for '{name}'[/yellow]")
            return

        table = Table(title=f"Version History: {name}")
        table.add_column("Version", style="cyan")
        table.add_column("Description")
        table.add_column("Installed At", style="green")

        for entry in history:
            table.add_row(
                entry["version"],
                entry.get("description", ""),
                entry.get("installed_at", ""),
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# ── 环境检查 ──────────────────────────────────────────────


@app.command()
def doctor() -> None:
    """检查安装和配置是否正常。"""
    console.print("[bold]Skills Manager Doctor[/bold]\n")

    # 检查版本
    console.print(f"  Version: {__version__}")

    # 检查存储目录
    store = Store()
    console.print(f"  Store path: {store.base_dir}")
    console.print(f"  Store exists: {'yes' if store.base_dir.exists() else 'no'}")

    # 检查已安装数量
    skills = store.list_all()
    console.print(f"  Installed skills: {len(skills)}")

    # 检查支持的格式
    formats = list_formats()
    console.print(f"  Supported formats: {', '.join(formats)}")

    # 检查依赖
    console.print("\n  [bold]Dependencies:[/bold]")
    deps = ["typer", "yaml", "rich"]
    for dep in deps:
        try:
            __import__(dep)
            console.print(f"    {dep}: OK")
        except ImportError:
            console.print(f"    {dep}: [red]MISSING[/red]")

    console.print("\n[green]All checks passed.[/green]")


# ── 更新检查 ──────────────────────────────────────────────────


@app.command()
def check_update() -> None:
    """检查是否有新版本可用。"""
    from .updater import check_update as do_check

    info = do_check()
    if info is None:
        console.print("[yellow]无法检查更新，请检查网络连接[/yellow]")
        return

    if info.has_update:
        console.print(
            f"[yellow]更新可用:[/yellow] v{info.latest_version} (当前 v{info.current_version})"
        )
        if info.release_url:
            console.print(f"  下载: [cyan]{info.release_url}[/cyan]")
    else:
        console.print(f"[green]已是最新版本 v{info.current_version}[/green]")


# ── 重分类 ──────────────────────────────────────────────────


@app.command()
def reclassify() -> None:
    """重新对所有已安装 Skill 运行自动分类。"""
    store = Store()
    changed = store.reclassify_all()
    if changed > 0:
        console.print(f"[green]OK[/green] Reclassified {changed} skills")
    else:
        console.print("All skills are already up to date")


# ── Claude Code 兼容性检查 ──────────────────────────────────


@app.command()
def check(
    fix: bool = typer.Option(False, "--fix", "-f", help="自动修复可修复的问题"),
) -> None:
    """检查 Claude Code skills 兼容性。"""
    from .claude_code_checker import ClaudeCodeChecker

    checker = ClaudeCodeChecker()
    reports = checker.scan()

    if not reports:
        console.print("[yellow]未找到 skills 目录[/yellow]")
        return

    console.print(checker.summary(reports))

    if fix:
        fixed = checker.auto_fix(reports)
        if fixed:
            console.print(f"\n[green]已修复 {fixed} 个 skill[/green]")
        else:
            console.print("\n没有需要修复的问题")


# ── Server ──────────────────────────────────────────────────


@app.command()
def serve(
    mode: str = typer.Option("mcp", "--mode", "-m", help="服务模式：mcp / api"),
    host: str = typer.Option("127.0.0.1", "--host", help="API 模式绑定的地址"),
    port: int = typer.Option(8000, "--port", "-p", help="API 模式绑定的端口"),
) -> None:
    """启动 skillfmt Server（MCP 或 HTTP API 模式）。"""
    if mode == "mcp":
        try:
            from .server import run_mcp_server
        except ImportError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        console.print("[green]启动 MCP Server（stdio 模式）...[/green]")
        run_mcp_server()
    elif mode == "api":
        try:
            from .server import create_app
            import uvicorn
        except ImportError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        console.print(f"[green]启动 HTTP API Server 于 {host}:{port} ...[/green]")
        app = create_app()
        uvicorn.run(app, host=host, port=port)
    else:
        console.print(f"[red]Error:[/red] Unknown mode '{mode}', expected: mcp / api")
        raise typer.Exit(1)


# ── MCP 配置管理 ──────────────────────────────────────────


mcp_app = typer.Typer(
    name="mcp",
    help="管理主流 MCP 客户端的 mcpServers 配置",
    no_args_is_help=True,
)
app.add_typer(mcp_app)


def _format_profile_status(prof) -> str:
    if prof.default_path is None:
        return "[dim]不可用[/dim]"
    return "[green]已存在[/green]" if prof.exists else "[yellow]未创建[/yellow]"


@mcp_app.command("profiles")
def mcp_profiles() -> None:
    """列出内置的 MCP 客户端 profile。"""
    from .mcp_config import MCPConfigManager

    mgr = MCPConfigManager()
    table = Table(title="MCP 客户端 Profile")
    table.add_column("ID", style="cyan")
    table.add_column("名称")
    table.add_column("路径", style="dim")
    table.add_column("状态")
    for prof in mgr.profiles():
        path = str(prof.default_path) if prof.default_path else "—"
        table.add_row(prof.id, prof.label, path, _format_profile_status(prof))
    console.print(table)


@mcp_app.command("list")
def mcp_list(
    profile: str = typer.Argument(..., help="profile id（如 claude-desktop）"),
) -> None:
    """列出指定 profile 下的所有 MCP server。"""
    from .mcp_config import MCPConfigError, MCPConfigManager

    try:
        servers = MCPConfigManager().list_servers(profile)
    except MCPConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    if not servers:
        console.print(f"[yellow]{profile} 当前没有任何 MCP server[/yellow]")
        return
    table = Table(title=f"{profile} - mcpServers ({len(servers)})")
    table.add_column("名称", style="cyan")
    table.add_column("Command")
    table.add_column("Args")
    table.add_column("状态")
    for s in servers:
        state = "[dim]disabled[/dim]" if s.disabled else "[green]enabled[/green]"
        table.add_row(s.name, s.command, " ".join(s.args), state)
    console.print(table)


@mcp_app.command("add")
def mcp_add(
    profile: str = typer.Argument(..., help="profile id"),
    name: str = typer.Argument(..., help="MCP server 名称"),
    command: str = typer.Option(..., "--command", "-c", help="可执行命令"),
    arg: list[str] = typer.Option([], "--arg", "-a", help="命令行参数，可重复指定"),
    env: list[str] = typer.Option(
        [], "--env", "-e", help="环境变量，格式 KEY=VALUE，可重复"
    ),
    disabled: bool = typer.Option(False, "--disabled", help="写入后立即禁用"),
) -> None:
    """新增或更新一个 MCP server。"""
    from .mcp_config import MCPConfigError, MCPConfigManager, MCPServer

    env_dict: dict[str, str] = {}
    for item in env:
        if "=" not in item:
            console.print(f"[red]Error:[/red] --env must be KEY=VALUE, got: {item}")
            raise typer.Exit(1)
        k, v = item.split("=", 1)
        env_dict[k.strip()] = v
    server = MCPServer(
        name=name, command=command, args=list(arg), env=env_dict, disabled=disabled
    )
    try:
        MCPConfigManager().add_or_update(profile, server)
    except MCPConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    console.print(f"[green]OK[/green] Wrote {name} into {profile}")


@mcp_app.command("remove")
def mcp_remove(
    profile: str = typer.Argument(..., help="profile id"),
    name: str = typer.Argument(..., help="MCP server 名称"),
) -> None:
    """从指定 profile 删除一个 MCP server。"""
    from .mcp_config import MCPConfigError, MCPConfigManager

    try:
        removed = MCPConfigManager().remove(profile, name)
    except MCPConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    if not removed:
        console.print(f"[yellow]{name} not present in {profile}[/yellow]")
        raise typer.Exit(1)
    console.print(f"[green]OK[/green] Removed {name} from {profile}")


@mcp_app.command("disable")
def mcp_disable(
    profile: str = typer.Argument(..., help="profile id"),
    name: str = typer.Argument(..., help="MCP server 名称"),
) -> None:
    """禁用一个 MCP server。"""
    from .mcp_config import MCPConfigError, MCPConfigManager

    try:
        ok = MCPConfigManager().set_disabled(profile, name, True)
    except MCPConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    if not ok:
        console.print(f"[yellow]{name} not present in {profile}[/yellow]")
        raise typer.Exit(1)
    console.print(f"[green]OK[/green] Disabled {name}")


@mcp_app.command("enable")
def mcp_enable(
    profile: str = typer.Argument(..., help="profile id"),
    name: str = typer.Argument(..., help="MCP server 名称"),
) -> None:
    """启用一个 MCP server。"""
    from .mcp_config import MCPConfigError, MCPConfigManager

    try:
        ok = MCPConfigManager().set_disabled(profile, name, False)
    except MCPConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    if not ok:
        console.print(f"[yellow]{name} not present in {profile}[/yellow]")
        raise typer.Exit(1)
    console.print(f"[green]OK[/green] Enabled {name}")


@mcp_app.command("install-skill")
def mcp_install_skill(
    profile: str = typer.Argument(..., help="profile id"),
    skill_name: str = typer.Argument(..., help="已安装的 skill 名称"),
    entry: str = typer.Option("server.py", "--entry", help="skill 目录中的入口脚本"),
    python: str = typer.Option(None, "--python", help="覆盖默认的 Python 解释器路径"),
) -> None:
    """把已安装的 skill 注册为指定 profile 的 MCP server。"""
    from .mcp_config import MCPConfigError, MCPConfigManager

    store = Store()
    try:
        skill = store.get(skill_name)
    except StoreError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    try:
        server = MCPConfigManager().install_skill_to(
            profile,
            skill_name=skill.name,
            skill_path=Path(skill.path),
            python_executable=python,
            entry=entry,
        )
    except MCPConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    console.print(
        f"[green]OK[/green] Wrote {skill.name} into {profile}, command={server.command}"
    )
