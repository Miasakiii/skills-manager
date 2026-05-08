"""适配器模块。

将 SkillIR 转换为各平台的工具定义格式。
"""

from .base import Adapter, AdapterError, get_adapter, list_formats
from .claude import ClaudeAdapter
from .gemini import GeminiAdapter
from .json_schema import JsonSchemaAdapter
from .mcp import MCPAdapter
from .openai import OpenAIAdapter

__all__ = [
    "Adapter",
    "AdapterError",
    "get_adapter",
    "list_formats",
    "OpenAIAdapter",
    "ClaudeAdapter",
    "GeminiAdapter",
    "MCPAdapter",
    "JsonSchemaAdapter",
]
