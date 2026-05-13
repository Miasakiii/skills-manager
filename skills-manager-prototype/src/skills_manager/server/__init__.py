"""skillfmt Server 模块。

提供 MCP Server 和 HTTP API 两种接口，
让 AI Agent 可以通过自然语言管理 skills。
"""

from __future__ import annotations

from .mcp_server import SkillfmtMCPServer, run_mcp_server

__all__ = ["SkillfmtMCPServer", "run_mcp_server", "create_app"]

try:
    from .api import create_app
except ImportError:

    def create_app(*args, **kwargs):
        raise RuntimeError("需要安装 fastapi：pip install skillfmt[server]")
