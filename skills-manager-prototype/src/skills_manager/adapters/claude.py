"""Claude Tool Use 格式适配器。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base import Adapter
from ..parser import parameters_to_json_schema

if TYPE_CHECKING:
    from ..ir import SkillIR


class ClaudeAdapter(Adapter):
    """Claude Tool Use 格式适配器。"""

    @property
    def name(self) -> str:
        return "claude"

    @property
    def file_extension(self) -> str:
        return ".json"

    def export(self, ir: SkillIR) -> str:
        schema = parameters_to_json_schema(ir.parameters)
        result = {
            "name": ir.name,
            "description": ir.description,
            "input_schema": schema,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
