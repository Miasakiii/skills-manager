"""打包与解包。

将 Skill 目录打包为 .skill 文件，以及从 .skill 文件解包。
支持导出为 Claude Desktop、Codex、Claude Code 等平台格式。
"""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path, PurePosixPath

from .parser import parse_skill_md


def pack(source_dir: Path, output_dir: Path | None = None) -> Path:
    """将 Skill 目录打包为 .skill 文件。

    Args:
        source_dir: Skill 目录（必须包含 SKILL.md）。
        output_dir: 输出目录，默认为 source_dir 的父目录。

    Returns:
        生成的 .skill 文件路径。
    """
    skill_md = source_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"No SKILL.md found in {source_dir}")

    ir = parse_skill_md(skill_md)
    output_dir = output_dir or source_dir.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{ir.name}-{ir.version}.skill"
    output_path = output_dir / filename

    with tarfile.open(output_path, "w:gz") as tar:
        # 顶层目录为 Skill 名称
        for item in source_dir.iterdir():
            if item.name.startswith("."):
                continue  # 跳过隐藏文件
            arcname = f"{ir.name}/{item.name}"
            tar.add(item, arcname=arcname)

    return output_path


def _validate_tar_member(member: tarfile.TarInfo, dest_dir: Path) -> bool:
    """验证 tar 成员路径是否安全（防止路径遍历）。"""
    target = dest_dir / member.name
    try:
        target.resolve().relative_to(dest_dir.resolve())
        return True
    except ValueError:
        return False


def _validate_zip_path(path: str, dest_dir: Path) -> bool:
    """验证 ZIP 内路径是否安全（防止路径遍历）。"""
    # 拒绝绝对路径和 .. 遍历
    parts = PurePosixPath(path).parts
    if any(p == ".." for p in parts):
        return False
    if PurePosixPath(path).is_absolute():
        return False
    return True


def unpack(package_path: Path, output_dir: Path | None = None) -> Path:
    """解包 .skill 文件。

    Args:
        package_path: .skill 文件路径。
        output_dir: 解压目标目录，默认为 package_path 的父目录。

    Returns:
        解压后的 Skill 目录路径。
    """
    if not package_path.exists():
        raise FileNotFoundError(f"Package not found: {package_path}")

    output_dir = output_dir or package_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(package_path, "r:gz") as tar:
        # 安全过滤：拒绝路径遍历成员
        safe_members = []
        for member in tar.getmembers():
            if not _validate_tar_member(member, output_dir):
                raise ValueError(f"Unsafe path in archive: {member.name}")
            safe_members.append(member)
        if hasattr(tarfile, "data_filter"):
            tar.extractall(output_dir, members=safe_members, filter="data")
        else:
            tar.extractall(output_dir, members=safe_members)

    # 找到解压后的目录
    for item in output_dir.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            return item

    # 如果顶层就有 SKILL.md
    if (output_dir / "SKILL.md").exists():
        return output_dir

    raise FileNotFoundError("No SKILL.md found in extracted package")


def pack_for_claude_desktop(skills_dirs: list[Path], output_dir: Path) -> Path:
    """打包为 Claude Desktop 格式（ZIP）。

    Claude Desktop 使用 Skill.md（注意是 Skill.md 不是 SKILL.md）作为 skill 定义文件。

    Args:
        skills_dirs: Skill 目录路径列表。
        output_dir: 输出目录。

    Returns:
        生成的 ZIP 文件路径。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "claude-desktop-skills.zip"

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for skill_dir in skills_dirs:
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            ir = parse_skill_md(skill_md)
            # Claude Desktop 使用 Skill.md 作为文件名
            arcname = f"{ir.name}/Skill.md"
            zf.write(skill_md, arcname)

            # 复制其他文件（排除隐藏文件和元数据）
            for item in skill_dir.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    rel_path = item.relative_to(skill_dir)
                    arc_path = f"{ir.name}/{rel_path}"
                    if _validate_zip_path(arc_path, output_dir):
                        zf.write(item, arc_path)

    return output_path


def pack_for_codex(skills_dirs: list[Path], output_dir: Path) -> Path:
    """打包为 Codex 格式（ZIP）。

    Codex 使用 .agents/skills/ 目录结构，每个 skill 一个目录。

    Args:
        skills_dirs: Skill 目录路径列表。
        output_dir: 输出目录。

    Returns:
        生成的 ZIP 文件路径。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "codex-skills.zip"

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for skill_dir in skills_dirs:
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            ir = parse_skill_md(skill_md)

            # 复制 skill 文件到 .agents/skills/{name}/
            for item in skill_dir.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    rel_path = item.relative_to(skill_dir)
                    arc_path = f".agents/skills/{ir.name}/{rel_path}"
                    if _validate_zip_path(arc_path, output_dir):
                        zf.write(item, arc_path)

        # 生成 AGENTS.md
        agents_md = _generate_agents_md(skills_dirs)
        zf.writestr("AGENTS.md", agents_md)

    return output_path


def pack_for_claude_code(skills_dirs: list[Path], output_dir: Path) -> Path:
    """打包为 Claude Code 格式（ZIP）。

    Claude Code 使用 .claude/skills/ 目录结构。

    Args:
        skills_dirs: Skill 目录路径列表。
        output_dir: 输出目录。

    Returns:
        生成的 ZIP 文件路径。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "claude-code-skills.zip"

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for skill_dir in skills_dirs:
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            ir = parse_skill_md(skill_md)

            # 复制 skill 文件到 .claude/skills/{name}/
            for item in skill_dir.rglob("*"):
                if item.is_file() and not item.name.startswith("."):
                    rel_path = item.relative_to(skill_dir)
                    arc_path = f".claude/skills/{ir.name}/{rel_path}"
                    if _validate_zip_path(arc_path, output_dir):
                        zf.write(item, arc_path)

    return output_path


def _generate_agents_md(skills_dirs: list[Path]) -> str:
    """生成 AGENTS.md 内容。"""
    lines = [
        "# Agents Configuration",
        "",
        "The following skills are available:",
        "",
    ]

    for skill_dir in skills_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        ir = parse_skill_md(skill_md)
        lines.append(f"- **{ir.name}**: {ir.description}")

    lines.append("")
    return "\n".join(lines)
