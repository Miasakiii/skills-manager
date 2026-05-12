"""YAML frontmatter 分割工具。

统一处理 SKILL.md 的 frontmatter 与 body 分离，消除 parser/validator 的重复逻辑。
"""

from __future__ import annotations


class FrontmatterError(ValueError):
    """Frontmatter 格式错误。"""


def split_frontmatter(content: str) -> tuple[str, str]:
    """分离 YAML frontmatter 和 Markdown body。

    Args:
        content: 完整的 SKILL.md 内容。

    Returns:
        (frontmatter_yaml, markdown_body) 元组。若无 frontmatter，返回 ("", content)。

    Raises:
        FrontmatterError: frontmatter 未闭合（以 --- 开头但无第二个 ---）。
    """
    content = content.lstrip("﻿")  # 去除 BOM

    if not content.startswith("---"):
        return "", content

    # 找第二个 ---
    second = content.find("---", 3)
    if second == -1:
        raise FrontmatterError("frontmatter 未闭合（缺少第二个 ---）")

    frontmatter = content[3:second].strip()
    body = content[second + 3 :].strip()
    return frontmatter, body
