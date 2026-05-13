"""skillfmt 内置 MCP Server。

将 skillfmt 的所有管理功能暴露为 MCP Tools，
供 Claude Desktop、Claude Code 等支持 MCP 的 Agent 调用。
"""

from __future__ import annotations

import json
from pathlib import Path

from ..logging import get_logger
from ..store import Store, StoreError

logger = get_logger(__name__)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    Server = None  # type: ignore[misc,assignment]


class SkillfmtMCPServer:
    """skillfmt MCP Server。

    暴露 tools:
    - list_skills: 列出所有已安装 skills
    - get_skill_info: 获取指定 skill 详情
    - search_skills: 搜索 skills
    - install_skill: 安装 skill
    - uninstall_skill: 卸载 skill
    - export_skill: 导出 skill 为指定格式
    - upgrade_skill: 升级 skill
    - rollback_skill: 回滚 skill
    - pack_skill: 打包 skill
    - doctor: 健康检查
    """

    def __init__(self, store: Store | None = None):
        if not _MCP_AVAILABLE:
            raise RuntimeError("需要安装 mcp 包：pip install skillfmt[server]")
        self.store = store or Store()
        self.server = Server("skillfmt")
        self._setup_tools()

    def _setup_tools(self) -> None:
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="list_skills",
                    description="列出所有已安装的 skills，返回名称、版本、分类和描述",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="get_skill_info",
                    description="获取指定 skill 的详细信息，包括参数、标签、作者等",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Skill 名称"},
                        },
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="search_skills",
                    description="按关键词搜索已安装的 skills",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"},
                            "category": {"type": "string", "description": "按分类筛选（可选）"},
                            "tag": {"type": "string", "description": "按标签筛选（可选）"},
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="install_skill",
                    description="从本地路径、URL 或 GitHub 仓库安装 skill",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "本地路径、URL 或 GitHub 仓库地址"},
                            "name": {"type": "string", "description": "自定义安装名（可选）"},
                            "force": {"type": "boolean", "description": "是否覆盖已有同名 skill"},
                        },
                        "required": ["source"],
                    },
                ),
                Tool(
                    name="uninstall_skill",
                    description="卸载指定 skill",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Skill 名称"},
                        },
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="export_skill",
                    description="将 skill 导出为指定平台格式（openai/claude/gemini/mcp/schema）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Skill 名称"},
                            "format": {"type": "string", "description": "目标格式：openai, claude, gemini, mcp, schema"},
                            "output": {"type": "string", "description": "输出文件路径（可选，默认返回内容）"},
                        },
                        "required": ["name", "format"],
                    },
                ),
                Tool(
                    name="upgrade_skill",
                    description="将已安装 skill 升级到新版本",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Skill 名称"},
                            "source": {"type": "string", "description": "新版本的本地目录路径"},
                        },
                        "required": ["name", "source"],
                    },
                ),
                Tool(
                    name="rollback_skill",
                    description="将 skill 回滚到上一个版本",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Skill 名称"},
                            "version": {"type": "string", "description": "目标版本号（可选，默认上一个版本）"},
                        },
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="pack_skill",
                    description="将 skill 目录打包为 .skill 文件",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "directory": {"type": "string", "description": "Skill 目录路径"},
                            "output": {"type": "string", "description": "输出目录（可选）"},
                        },
                        "required": ["directory"],
                    },
                ),
                Tool(
                    name="doctor",
                    description="检查 skillfmt 安装和配置状态",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return await self._handle_tool(name, arguments)

    async def _handle_tool(self, name: str, arguments: dict) -> list:
        from ..adapters import get_adapter, list_formats
        from ..packager import pack

        try:
            if name == "list_skills":
                skills = self.store.list_all()
                data = [
                    {
                        "name": s.name,
                        "version": s.version,
                        "category": getattr(s, "category", None),
                        "description": getattr(s, "description", ""),
                    }
                    for s in skills
                ]
                return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

            if name == "get_skill_info":
                skill_name = arguments["name"]
                skill = self.store.get(skill_name)
                ir = self.store.get_skill_ir(skill_name)
                data = {
                    "name": ir.name,
                    "version": ir.version,
                    "description": ir.description,
                    "summary": ir.summary,
                    "type": ir.type,
                    "skill_type": ir.skill_type,
                    "intent": ir.intent,
                    "tags": ir.tags,
                    "category": ir.category,
                    "author": ir.author,
                    "license": ir.license,
                    "parameters": [
                        {"name": p.name, "type": p.type, "description": p.description, "required": p.required}
                        for p in ir.parameters
                    ],
                    "installed_at": getattr(skill, "installed_at", ""),
                    "source": getattr(skill, "source", ""),
                }
                return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

            if name == "search_skills":
                results = self.store.search(
                    arguments["query"],
                    tag=arguments.get("tag"),
                    category=arguments.get("category"),
                )
                data = [
                    {
                        "name": s.name,
                        "version": s.version,
                        "category": getattr(s, "category", None),
                        "description": getattr(s, "description", ""),
                    }
                    for s in results
                ]
                return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

            if name == "install_skill":
                source = arguments["source"]
                force = arguments.get("force", False)
                custom_name = arguments.get("name")
                source_path = Path(source)

                if source.startswith(("http://", "https://")):
                    result = self.store.install_from_url(source)
                elif source_path.suffix == ".skill":
                    result = self.store.install_from_package(source_path)
                else:
                    result = self.store.install(source_path, name=custom_name, force=force)

                msg = f"已安装 {result.name} v{result.version}"
                return [TextContent(type="text", text=msg)]

            if name == "uninstall_skill":
                self.store.uninstall(arguments["name"])
                return [TextContent(type="text", text=f"已卸载 {arguments['name']}")]

            if name == "export_skill":
                skill_name = arguments["name"]
                fmt = arguments["format"]
                output = arguments.get("output")

                ir = self.store.get_skill_ir(skill_name)
                adapter = get_adapter(fmt)
                content = adapter.export(ir)

                if output:
                    out_path = Path(output)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(content, encoding="utf-8")
                    msg = f"已导出到 {out_path}"
                else:
                    msg = content

                self.store.add_export_history(skill_name, fmt, output or "stdout")
                return [TextContent(type="text", text=msg)]

            if name == "upgrade_skill":
                result = self.store.upgrade(arguments["name"], Path(arguments["source"]))
                return [TextContent(type="text", text=f"已升级 {result.name} 到 v{result.version}")]

            if name == "rollback_skill":
                result = self.store.rollback(arguments["name"], arguments.get("version"))
                return [TextContent(type="text", text=f"已回滚 {result.name} 到 v{result.version}")]

            if name == "pack_skill":
                out = arguments.get("output")
                result = pack(
                    Path(arguments["directory"]),
                    Path(out) if out else None,
                )
                return [TextContent(type="text", text=f"已打包到 {result}")]

            if name == "doctor":
                skills = self.store.list_all()
                formats = list_formats()
                data = {
                    "status": "ok",
                    "store_path": str(self.store.base_dir),
                    "installed_skills": len(skills),
                    "supported_formats": formats,
                }
                return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]

            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except StoreError as e:
            return [TextContent(type="text", text=f"Error: {e}")]
        except Exception as e:
            logger.exception("MCP tool error: %s", name)
            return [TextContent(type="text", text=f"Error: {e}")]

    async def run(self) -> None:
        """启动 MCP Server（stdio 模式）。"""
        async with stdio_server() as (read, write):
            await self.server.run(read, write)


def run_mcp_server() -> None:
    """启动 skillfmt MCP Server。"""
    import asyncio

    server = SkillfmtMCPServer()
    asyncio.run(server.run())
