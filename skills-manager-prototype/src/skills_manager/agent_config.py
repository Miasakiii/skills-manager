"""Agent 配置生成器。

生成 CLAUDE.md 等配置文件，让 agent 知道有哪些 skill 可用。
"""

from __future__ import annotations

from pathlib import Path

from skills_manager.logging import get_logger

logger = get_logger(__name__)


def generate_claude_md(skills: list) -> str:
    """生成 CLAUDE.md 内容，列出所有可用 skill。

    Args:
        skills: skill 信息列表，每个包含 name、skill_type、description。
               支持字典或对象格式。

    Returns:
        CLAUDE.md 文件内容。
    """
    if not skills:
        return "# Skills Manager — Agent 配置\n\n暂无已安装的 skill。\n"

    lines = [
        "# Skills Manager — Agent 配置",
        "",
        "以下 skill 已安装并可用：",
        "",
        "| 名称 | 类型 | 描述 |",
        "| ---- | ---- | ---- |",
    ]

    for s in skills:
        # 支持字典和对象两种格式
        if isinstance(s, dict):
            name = s.get("name", "")
            skill_type = s.get("skill_type", "")
            description = s.get("description", "")
        else:
            name = getattr(s, "name", "")
            skill_type = getattr(s, "skill_type", "")
            description = getattr(s, "description", "")
        lines.append(f"| {name} | {skill_type} | {description} |")

    lines.extend([
        "",
        "使用方式：在对话中引用 skill 名称即可。",
        "",
    ])

    return "\n".join(lines)


def update_agent_claude_md(agent_dir: Path, skills: list) -> bool:
    """更新 agent 目录中的 CLAUDE.md。

    Args:
        agent_dir: agent 目录路径。
        skills: skill 信息列表，支持字典或对象格式。

    Returns:
        是否成功更新。
    """
    try:
        claude_md = agent_dir / "CLAUDE.md"
        content = generate_claude_md(skills)
        claude_md.write_text(content, encoding="utf-8")
        return True
    except Exception:
        logger.exception("Failed to write CLAUDE.md to %s", agent_dir)
        return False
