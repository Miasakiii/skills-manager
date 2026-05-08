"""Gemini Function Declaration 格式适配器。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base import Adapter
from ..ir import Parameter

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
        params = self._parameters_to_schema(ir.parameters)
        result = {
            "function_declarations": [
                {
                    "name": ir.name,
                    "description": ir.description,
                    "parameters": params,
                }
            ]
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _parameters_to_schema(self, parameters: list[Parameter]) -> dict:
        """将参数转换为 Gemini 格式的 schema（类型名大写）。"""
        properties = {}
        required = []

        for p in parameters:
            gemini_type = GEMINI_TYPE_MAP.get(p.type, "STRING")
            prop: dict = {"type": gemini_type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        schema: dict = {"type": "OBJECT", "properties": properties}
        if required:
            schema["required"] = required

        return schema
