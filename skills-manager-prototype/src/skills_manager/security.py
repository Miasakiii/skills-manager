"""安全工具：输入清理与路径穿越防护。"""

from __future__ import annotations

import re
from pathlib import Path

# name 字段允许的字符：字母、数字、连字符、下划线、点（不能以点开头）
_NAME_RE = re.compile(r"[^a-zA-Z0-9\-_.]")
# 连续的路径分隔符或递归目录
_PATH_TRAVERSAL_RE = re.compile(r"\.\.[/\\]|[/\\]\.\.|~")

_NAME_MAX_LENGTH = 64


def sanitize_name(name: str) -> str:
    """清理 Skill 名称，防止路径穿越和非法字符。

    规则：
    - 移除 NUL 字节
    - 移除路径分隔符
    - 拒绝 ``..`` 和 ``~`` 等路径穿越模式
    - 只保留安全字符（字母、数字、-、_、.）
    - 不能以 ``.`` 开头（防止隐藏文件）
    - 截断到 64 字符
    - 空字符串返回 "untitled"
    """
    if not name:
        return "untitled"

    # 移除 NUL 字节
    name = name.replace("\x00", "")

    # 拒绝路径穿越模式
    if _PATH_TRAVERSAL_RE.search(name):
        name = _PATH_TRAVERSAL_RE.sub("_", name)

    # 移除路径分隔符
    name = name.replace("/", "-").replace("\\", "-")

    # 只保留安全字符
    name = _NAME_RE.sub("-", name)

    # 压缩连续连字符
    while "--" in name:
        name = name.replace("--", "-")

    # 去除首尾连字符和点
    name = name.strip("-.")
    # 不能以点开头
    if name.startswith("."):
        name = name[1:]

    # 截断
    if len(name) > _NAME_MAX_LENGTH:
        name = name[:_NAME_MAX_LENGTH].rstrip("-.")

    # 最终兜底
    if not name:
        return "untitled"

    return name


def validate_path_safety(target: Path, parent: Path) -> bool:
    """确认 target 解析后在 parent 目录内（防符号链接穿越）。

    Returns:
        True 如果 target 安全地处于 parent 目录树下。
    """
    try:
        resolved = parent.resolve()
        target_resolved = (parent / target).resolve()
        # 使用 os.path.commonpath 判断是否在父目录内
        target_str = str(target_resolved)
        parent_str = str(resolved)
        return target_str.startswith(parent_str + str(Path("/" if target_str != parent_str else "")))
    except (OSError, ValueError):
        return False
