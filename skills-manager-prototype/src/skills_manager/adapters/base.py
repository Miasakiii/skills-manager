"""适配器基类与注册。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ir import SkillIR


class AdapterError(Exception):
    """适配器错误。"""


class Adapter(ABC):
    """所有适配器的基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称，如 'openai', 'claude'。"""
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """输出文件扩展名，如 '.json', '.py'。"""
        ...

    @abstractmethod
    def export(self, ir: SkillIR) -> str:
        """将 IR 转换为目标格式的字符串。"""
        ...

    def export_batch(self, irs: list[SkillIR]) -> str:
        """批量导出多个 IR。"""
        import json

        results = []
        for ir in irs:
            content = self.export(ir)
            try:
                results.append(json.loads(content))
            except json.JSONDecodeError:
                results.append(content)
        return json.dumps(results, indent=2, ensure_ascii=False)


# 适配器注册表
_REGISTRY: dict[str, Adapter] = {}


def register(adapter: Adapter) -> None:
    """注册适配器。"""
    _REGISTRY[adapter.name] = adapter


def get_adapter(format_name: str) -> Adapter:
    """获取指定格式的适配器。

    Raises:
        ValueError: 不支持的格式。
    """
    _ensure_registered()
    if format_name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(f"Unsupported format: {format_name}. Available: {available}")
    return _REGISTRY[format_name]


def list_formats() -> list[str]:
    """列出所有支持的格式。"""
    _ensure_registered()
    return sorted(_REGISTRY.keys())


def _ensure_registered() -> None:
    """确保所有内置适配器已注册。"""
    if _REGISTRY:
        return
    from .claude import ClaudeAdapter
    from .gemini import GeminiAdapter
    from .json_schema import JsonSchemaAdapter
    from .mcp import MCPAdapter
    from .openai import OpenAIAdapter

    register(OpenAIAdapter())
    register(ClaudeAdapter())
    register(GeminiAdapter())
    register(MCPAdapter())
    register(JsonSchemaAdapter())
