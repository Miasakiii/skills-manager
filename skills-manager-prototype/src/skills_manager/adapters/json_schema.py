"""纯 JSON Schema 格式适配器。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base import Adapter
from ..parser import parameters_to_json_schema

if TYPE_CHECKING:
    from ..ir import SkillIR


class JsonSchemaAdapter(Adapter):
    """纯 JSON Schema 格式适配器。"""

    @property
    def name(self) -> str:
        return "schema"

    @property
    def file_extension(self) -> str:
        return ".json"

    def export(self, ir: SkillIR) -> str:
        schema = parameters_to_json_schema(ir.parameters)
        result = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": ir.name,
            "description": ir.description,
            **schema,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
