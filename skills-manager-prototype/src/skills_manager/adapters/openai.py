"""OpenAI Function Calling 格式适配器。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base import Adapter
from ..parser import parameters_to_json_schema

if TYPE_CHECKING:
    from ..ir import SkillIR


class OpenAIAdapter(Adapter):
    """OpenAI Function Calling 格式适配器。"""

    @property
    def name(self) -> str:
        return "openai"

    @property
    def file_extension(self) -> str:
        return ".json"

    def export(self, ir: SkillIR) -> str:
        schema = parameters_to_json_schema(ir.parameters)
        result = {
            "type": "function",
            "function": {
                "name": ir.name,
                "description": ir.description,
                "parameters": schema,
                "strict": True,
            },
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
