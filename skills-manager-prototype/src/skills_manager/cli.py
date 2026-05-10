"""CLI 命令行入口。"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .adapters import get_adapter, list_formats
from .ir import SkillIR
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
            console.print("[red]Error:[/red] Please specify a skill name or use --current-dir")
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
    name: str = typer.Argument(..., help="Skill 名称"),
) -> None:
    """卸载 Skill。"""
    store = Store()
    try:
        store.uninstall(name)
        console.print(f"[green]OK[/green] Uninstalled {name}")
    except StoreError as e:
        console.print(f"[red]Error:[/red] {e}")
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
        console.print("[yellow]No installed skills. Use 'skills install' to add.[/yellow]")
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
    from .updater import check_update as do_check, format_update_message

    info = do_check()
    if info is None:
        console.print("[yellow]无法检查更新，请检查网络连接[/yellow]")
        return

    if info.has_update:
        console.print(f"[yellow]更新可用:[/yellow] v{info.latest_version} (当前 v{info.current_version})")
        if info.release_url:
            console.print(f"  下载: [cyan]{info.release_url}[/cyan]")
    else:
        console.print(f"[green]已是最新版本 v{info.current_version}[/green]")


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
