"""中间表示（IR）数据结构定义。

IR 是所有适配器的统一输入，从 SKILL.md 解析生成。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Parameter:
    """工具参数定义。"""

    name: str
    type: str  # "string" | "integer" | "number" | "boolean" | "array" | "object"
    description: str = ""
    required: bool = False
    enum: list[str] | None = None
    default: Any = None


@dataclass
class Example:
    """输入输出示例。"""

    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutorConfig:
    """执行配置。"""

    type: str  # "python" | "node" | "shell" | "http"
    entry: str = ""
    function: str | None = None


@dataclass
class SecurityConfig:
    """安全声明。"""

    needs_network: bool = False
    needs_api_key: bool = False


@dataclass
class SkillIR:
    """Skill 的中间表示。

    从 SKILL.md 解析生成，作为所有适配器的统一输入。
    """

    # 核心标识
    name: str
    version: str
    description: str
    summary: str = ""
    type: str = "tool"  # "prompt" | "tool" | "workflow" | "composite"
    skill_type: str = ""  # "component" | "interactive" | "workflow"（语义类型）
    intent: str = ""  # 详细意图说明

    # 参数定义
    parameters: list[Parameter] = field(default_factory=list)

    # 文档
    functionality: str = ""
    use_cases: list[str] = field(default_factory=list)
    not_for: list[str] = field(default_factory=list)
    examples: list[Example] = field(default_factory=list)

    # 分类
    tags: list[str] = field(default_factory=list)
    category: str | None = None

    # 执行配置
    executor: ExecutorConfig | None = None
    security: SecurityConfig | None = None
    config: dict[str, Any] | None = None

    # 元信息
    author: str | None = None
    license: str | None = None
