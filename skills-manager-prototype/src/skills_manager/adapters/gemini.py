"""Gemini Function Declaration 格式适配器。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base import Adapter
from ..ir import parameters_to_json_schema

if TYPE_CHECKING:
    from ..ir import SkillIR


# JSON Schema 类型 → Gemini 类型
GEMINI_TYPE_MAP = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
}


class GeminiAdapter(Adapter):
    """Gemini Function Declaration 格式适配器。"""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def file_extension(self) -> str:
        return ".json"

    def export(self, ir: SkillIR) -> str:
        schema = parameters_to_json_schema(ir.parameters)
        gemini_schema = self._to_gemini_types(schema)
        result = {
            "function_declarations": [
                {
                    "name": ir.name,
                    "description": ir.description,
                    "parameters": gemini_schema,
                }
            ]
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _to_gemini_types(
        self, node: dict | list | str | int | bool | None
    ) -> dict | list | str | int | bool | None:
        """递归将 JSON Schema 中的类型名转换为 Gemini 大写格式。"""
        if isinstance(node, dict):
            result = {}
            for key, value in node.items():
                if key == "type" and isinstance(value, str):
                    result[key] = GEMINI_TYPE_MAP.get(value, value.upper())
                elif isinstance(value, (dict, list)):
                    result[key] = self._to_gemini_types(value)
                else:
                    result[key] = value
            return result
        elif isinstance(node, list):
            return [self._to_gemini_types(item) for item in node]
        return node
