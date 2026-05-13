"""SKILL.md 解析器。

解析 YAML frontmatter + Markdown body，生成 SkillIR。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .frontmatter import FrontmatterError, split_frontmatter
from .ir import (
    Example,
    ExecutorConfig,
    Parameter,
    SecurityConfig,
    SkillIR,
)
from .security import sanitize_name

# Markdown 类型 → JSON Schema 类型
TYPE_MAP: dict[str, str] = {
    "string": "string",
    "str": "string",
    "int": "integer",
    "integer": "integer",
    "float": "number",
    "number": "number",
    "bool": "boolean",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
    "string[]": "array",
}


class ParseError(Exception):
    """解析错误。"""

    def __init__(self, message: str, line: int | None = None):
        self.line = line
        super().__init__(f"Line {line}: {message}" if line else message)


def parse_skill_md(path: Path) -> SkillIR:
    """解析 SKILL.md 文件，返回 IR。

    Args:
        path: SKILL.md 文件路径。

    Returns:
        解析后的 SkillIR 对象。

    Raises:
        ParseError: 解析失败时抛出。
        FileNotFoundError: 文件不存在时抛出。
    """
    content = path.read_text(encoding="utf-8")
    return parse_skill_content(content, name_hint=path.parent.name)


def parse_skill_content(content: str, name_hint: str = "") -> SkillIR:
    """解析 SKILL.md 内容字符串，返回 IR。

    Args:
        content: SKILL.md 的完整文本内容。
        name_hint: 当 frontmatter 中没有 name 时使用的备选名称。

    Returns:
        解析后的 SkillIR 对象。
    """
    try:
        frontmatter, body = split_frontmatter(content)
    except FrontmatterError:
        frontmatter, body = "", content

    # 解析 frontmatter
    fm = yaml.safe_load(frontmatter) or {}

    # 解析 Markdown body
    functionality = _extract_section(body, "功能")
    param_rows = _extract_table(body, "参数")
    _return_rows = _extract_table(body, "返回")  # 存储备用
    examples = _extract_examples(body)
    use_cases = _extract_list(body, "适用场景")
    not_for = _extract_list(body, "不适用")

    # 构建参数列表
    parameters = _parse_parameters(param_rows)

    return SkillIR(
        name=sanitize_name(fm.get("name") or name_hint),
        version=str(fm.get("version", "0.0.0")),
        description=fm.get("description", ""),
        summary=fm.get("summary", fm.get("description", "")),
        type=fm.get("type", "tool"),
        skill_type=fm.get("skill_type", ""),
        intent=fm.get("intent", ""),
        parameters=parameters,
        functionality=functionality,
        use_cases=use_cases,
        not_for=not_for,
        examples=examples,
        tags=fm.get("tags", []) or [],
        category=fm.get("category"),
        executor=_parse_executor(fm.get("executor")),
        security=_parse_security(fm.get("security")),
        config=fm.get("config"),
        author=fm.get("author"),
        license=fm.get("license"),
    )


def _extract_section(body: str, header: str) -> str:
    """提取 Markdown 中指定标题下的内容（直到下一个同级标题）。"""
    pattern = rf"^##\s+{re.escape(header)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, body, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_table(body: str, header: str) -> list[dict[str, str]]:
    """提取 Markdown 中指定标题下的表格，返回字典列表。

    解析逻辑：
    1. 定位 ## 标题
    2. 找到表格（以 | 开头的行）
    3. 第一行为表头，跳过分隔行，后续为数据行
    """
    section = _extract_section(body, header)
    if not section:
        return []

    lines = [line.strip() for line in section.split("\n") if line.strip()]

    # 找表格起始位置
    table_start = None
    for i, line in enumerate(lines):
        if line.startswith("|"):
            table_start = i
            break

    if table_start is None:
        return []

    table_lines = lines[table_start:]
    if len(table_lines) < 3:  # 至少：表头 + 分隔行 + 一行数据
        return []

    # 解析表头
    headers = [h.strip() for h in table_lines[0].split("|") if h.strip()]

    # 跳过分隔行（第二行），解析数据行
    rows = []
    for line in table_lines[2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))

    return rows


def _parse_parameters(param_rows: list[dict[str, str]]) -> list[Parameter]:
    """将表格行解析为 Parameter 列表。"""
    parameters = []

    for row in param_rows:
        # 兼容中英文表头
        name = row.get("参数", row.get("name", "")).strip()
        if not name:
            continue

        type_str = row.get("类型", row.get("type", "string")).strip().lower()
        desc = row.get("说明", row.get("description", "")).strip()
        req_str = row.get("必需", row.get("required", "")).strip()

        json_type = TYPE_MAP.get(type_str, "string")

        # 检测枚举值：说明中包含 "X / Y / Z" 格式
        enum_values = _detect_enum(desc)

        required = req_str in ("✅", "是", "yes", "true", "Y", "✓")

        parameters.append(
            Parameter(
                name=name,
                type=json_type,
                description=desc,
                required=required,
                enum=enum_values,
            )
        )

    return parameters


def _detect_enum(text: str) -> list[str] | None:
    """从文本中检测枚举值。

    匹配模式：
    - ：zh / en / ja / ko
    - : zh / en / ja / ko
    - zh,en,ja,ko
    """
    # 模式1: X / Y / Z（前面有冒号）
    match = re.search(r"[：:]\s*([\w_-]+(?:\s*/\s*[\w_-]+)+)", text)
    if match:
        return [v.strip() for v in match.group(1).split("/")]

    # 模式2: X,Y,Z（前面有冒号）
    match = re.search(r"[：:]\s*([\w_-]+(?:\s*,\s*[\w_-]+)+)", text)
    if match:
        return [v.strip() for v in match.group(1).split(",")]

    return None


def _extract_examples(body: str) -> list[Example]:
    """从 Markdown body 中提取 JSON 示例。"""
    section = _extract_section(body, "示例")
    if not section:
        return []

    examples = []

    # 查找 JSON 代码块
    json_blocks = re.findall(r"```(?:json)?\s*\n(.*?)```", section, re.DOTALL)

    # 尝试配对：奇数位为 input，偶数位为 output
    i = 0
    while i < len(json_blocks):
        input_data = _try_parse_json(json_blocks[i])
        output_data = {}
        if i + 1 < len(json_blocks):
            output_data = _try_parse_json(json_blocks[i + 1])
            i += 2
        else:
            i += 1

        if input_data or output_data:
            examples.append(Example(input=input_data, output=output_data))

    return examples


def _try_parse_json(text: str) -> dict:
    """尝试解析 JSON，失败返回空字典。"""
    text = text.strip()
    if not text:
        return {}
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        return {}


def _extract_list(body: str, header: str) -> list[str]:
    """提取 Markdown 中指定标题下的列表项。"""
    section = _extract_section(body, header)
    if not section:
        return []

    items = []
    for line in section.split("\n"):
        line = line.strip()
        # 匹配 - item 或 * item
        match = re.match(r"^[-*]\s+(.+)", line)
        if match:
            items.append(match.group(1).strip())

    return items


def _parse_executor(data: dict | None) -> ExecutorConfig | None:
    """解析执行配置。"""
    if not data or not isinstance(data, dict):
        return None
    return ExecutorConfig(
        type=data.get("type", "python"),
        entry=data.get("entry", ""),
        function=data.get("function"),
    )


def _parse_security(data: dict | None) -> SecurityConfig | None:
    """解析安全配置。"""
    if not data or not isinstance(data, dict):
        return None
    return SecurityConfig(
        needs_network=data.get("needs_network", False),
        needs_api_key=data.get("needs_api_key", False),
    )


# 向后兼容：从 ir 重新导出
from .ir import parameters_to_json_schema  # noqa: E402, F401
