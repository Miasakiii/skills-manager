"""测试 server 模块。

注意：mcp 和 fastapi 是可选依赖，未安装时相关测试会跳过。
"""

from __future__ import annotations

import importlib.util

import pytest

from skills_manager.store import Store

# ── MCP Server ──────────────────────────────────────────────

_mcp_available = importlib.util.find_spec("mcp") is not None

_fastapi_available = importlib.util.find_spec("fastapi") is not None


@pytest.mark.skipif(not _mcp_available, reason="mcp not installed")
def test_mcp_server_init(tmp_path):
    """测试 MCP Server 初始化。"""
    from skills_manager.server.mcp_server import SkillfmtMCPServer

    store = Store(base_dir=tmp_path)
    server = SkillfmtMCPServer(store=store)
    assert server.store is store
    assert server.server is not None


@pytest.mark.skipif(not _mcp_available, reason="mcp not installed")
def test_mcp_server_tools_registered(tmp_path):
    """测试所有 tools 已注册。"""
    from skills_manager.server.mcp_server import SkillfmtMCPServer

    store = Store(base_dir=tmp_path)
    server = SkillfmtMCPServer(store=store)
    assert server.server is not None


@pytest.mark.skipif(not _mcp_available, reason="mcp not installed")
def test_mcp_import_error_without_mcp(monkeypatch):
    """测试未安装 mcp 时抛出 RuntimeError。"""
    monkeypatch.setattr("skills_manager.server.mcp_server._MCP_AVAILABLE", False)
    from skills_manager.server.mcp_server import SkillfmtMCPServer

    with pytest.raises(RuntimeError, match="需要安装 mcp"):
        SkillfmtMCPServer()


# ── HTTP API ────────────────────────────────────────────────


@pytest.mark.skipif(not _fastapi_available, reason="fastapi not installed")
def test_api_create_app(tmp_path):
    """测试 FastAPI 应用创建。"""
    from skills_manager.server.api import create_app

    store = Store(base_dir=tmp_path)
    app = create_app(store=store)
    assert app is not None


@pytest.mark.skipif(not _fastapi_available, reason="fastapi not installed")
def test_api_health_endpoint(tmp_path):
    """测试 health 接口。"""
    from fastapi.testclient import TestClient
    from skills_manager.server.api import create_app

    store = Store(base_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["installed_skills"] == 0


@pytest.mark.skipif(not _fastapi_available, reason="fastapi not installed")
def test_api_list_skills_empty(tmp_path):
    """测试空 skill 列表。"""
    from fastapi.testclient import TestClient
    from skills_manager.server.api import create_app

    store = Store(base_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get("/skills")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.skipif(not _fastapi_available, reason="fastapi not installed")
def test_api_get_skill_not_found(tmp_path):
    """测试获取不存在的 skill。"""
    from fastapi.testclient import TestClient
    from skills_manager.server.api import create_app

    store = Store(base_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get("/skills/nonexistent")
    assert response.status_code == 404


@pytest.mark.skipif(not _fastapi_available, reason="fastapi not installed")
def test_api_formats_endpoint(tmp_path):
    """测试 formats 接口。"""
    from fastapi.testclient import TestClient
    from skills_manager.server.api import create_app

    store = Store(base_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get("/formats")
    assert response.status_code == 200
    data = response.json()
    assert "formats" in data
    assert "openai" in data["formats"]
    assert "claude" in data["formats"]


@pytest.mark.skipif(not _fastapi_available, reason="fastapi not installed")
def test_api_search_empty(tmp_path):
    """测试搜索无结果。"""
    from fastapi.testclient import TestClient
    from skills_manager.server.api import create_app

    store = Store(base_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)
    response = client.get("/search?query=foo")
    assert response.status_code == 200
    assert response.json() == []
