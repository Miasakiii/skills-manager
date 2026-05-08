"""打包与解包。

将 Skill 目录打包为 .skill 文件，以及从 .skill 文件解包。
"""

from __future__ import annotations

import tarfile
from pathlib import Path

from .ir import SkillIR
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
        tar.extractall(output_dir)

    # 找到解压后的目录
    for item in output_dir.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            return item

    # 如果顶层就有 SKILL.md
    if (output_dir / "SKILL.md").exists():
        return output_dir

    raise FileNotFoundError("No SKILL.md found in extracted package")
