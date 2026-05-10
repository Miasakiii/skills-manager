"""Skill 格式验证器。

在安装前检查 SKILL.md 是否合规，避免无效 skill 进入 store。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .ir import SkillIR
from .logging import get_logger
from .parser import ParseError, parse_skill_content

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """验证结果。"""

    valid: bool
    errors: list[str] = field(default_factory=list)  # 必须修复
    warnings: list[str] = field(default_factory=list)  # 建议修复


def validate_skill_dir(path: Path) -> ValidationResult:
    """验证 skill 目录是否合规。

    Args:
        path: skill 目录路径。

    Returns:
        验证结果。
    """
    result = ValidationResult(valid=True)

    # 检查目录是否存在
    if not path.is_dir():
        result.valid = False
        result.errors.append(f"目录不存在: {path}")
        return result

    # 检查 SKILL.md 是否存在
    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        result.valid = False
        result.errors.append("缺少 SKILL.md 文件")
        return result

    # 读取并验证 SKILL.md 内容
    try:
        content = skill_md.read_text(encoding="utf-8")
        md_result = validate_skill_md(content, dir_name=path.name)
        result.errors.extend(md_result.errors)
        result.warnings.extend(md_result.warnings)
        if md_result.errors:
            result.valid = False
    except Exception as e:
        result.valid = False
        result.errors.append(f"读取 SKILL.md 失败: {e}")

    return result


def validate_skill_md(content: str, dir_name: str = "") -> ValidationResult:
    """验证 SKILL.md 内容是否合规。

    Args:
        content: SKILL.md 的完整文本内容。
        dir_name: 所在目录名（用于检查与 name 字段是否一致）。

    Returns:
        验证结果。
    """
    result = ValidationResult(valid=True)

    # 分离 frontmatter
    if not content.startswith("---"):
        result.valid = False
        result.errors.append("缺少 YAML frontmatter（应以 --- 开头）")
        return result

    second = content.find("---", 3)
    if second == -1:
        result.valid = False
        result.errors.append("frontmatter 未闭合（缺少第二个 ---）")
        return result

    frontmatter_yaml = content[3:second].strip()

    # 解析 YAML
    try:
        fm = yaml.safe_load(frontmatter_yaml)
        if not isinstance(fm, dict):
            result.valid = False
            result.errors.append("frontmatter 不是有效的 YAML 字典")
            return result
    except yaml.YAMLError as e:
        result.valid = False
        result.errors.append(f"frontmatter YAML 解析失败: {e}")
        logger.warning("YAML 解析失败: %s", e)
        return result

    # 检查必填字段
    if not fm.get("name"):
        result.valid = False
        result.errors.append("缺少必填字段: name")

    if not fm.get("description"):
        result.valid = False
        result.errors.append("缺少必填字段: description")

    # 检查字段长度（警告）
    name = fm.get("name", "")
    if len(name) > 64:
        result.warnings.append(f"name 长度 {len(name)} 超过 64 字符（Claude Desktop 兼容性）")

    description = fm.get("description", "")
    if len(description) > 200:
        result.warnings.append(f"description 长度 {len(description)} 超过 200 字符（Claude Desktop 兼容性）")

    # 检查目录名与 name 是否一致（警告）
    if dir_name and name and dir_name != name:
        result.warnings.append(f"目录名 '{dir_name}' 与 name 字段 '{name}' 不一致")

    # 检查 skill_type 值是否合法（警告）
    valid_skill_types = {"component", "interactive", "workflow", ""}
    skill_type = fm.get("skill_type", "")
    if skill_type and skill_type not in valid_skill_types:
        result.warnings.append(f"skill_type 值 '{skill_type}' 不合法，应为 component/interactive/workflow")

    return result


def validate_and_parse(content: str, dir_name: str = "") -> tuple[ValidationResult, SkillIR | None]:
    """验证并解析 SKILL.md 内容。

    Args:
        content: SKILL.md 的完整文本内容。
        dir_name: 所在目录名。

    Returns:
        (验证结果, 解析后的 IR 或 None) 元组。
    """
    result = validate_skill_md(content, dir_name)

    if not result.valid:
        return result, None

    try:
        ir = parse_skill_content(content, name_hint=dir_name)
        return result, ir
    except ParseError as e:
        result.valid = False
        result.errors.append(f"解析失败: {e}")
        return result, None
