"""MCP Server 生成适配器。"""

from __future__ import annotations

import json
import textwrap
from typing import TYPE_CHECKING

from .base import Adapter
from ..parser import parameters_to_json_schema

if TYPE_CHECKING:
    from ..ir import SkillIR


class MCPAdapter(Adapter):
    """MCP Server Python 脚本生成适配器。"""

    @property
    def name(self) -> str:
        return "mcp"

    @property
    def file_extension(self) -> str:
        return ".py"

    def export(self, ir: SkillIR) -> str:
        schema = parameters_to_json_schema(ir.parameters)
        schema_json = json.dumps(schema, indent=4, ensure_ascii=False)
        schema_indented = textwrap.indent(schema_json, " " * 12)

        function_name = "run"
        if ir.executor and ir.executor.function:
            function_name = ir.executor.function

        return f'''#!/usr/bin/env python3
"""MCP Server for {ir.name} - {ir.description}"""

from mcp.server import Server
from mcp.types import Tool
import json

server = Server("{ir.name}")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="{ir.name}",
            description="{ir.description}",
            inputSchema={schema_indented},
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    # TODO: 实现工具调用逻辑
    # 可以直接调用 handler.py 中的函数
    from handler import {function_name}
    return {function_name}(**arguments)


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read, write):
            await server.run(read, write)

    asyncio.run(main())
'''
