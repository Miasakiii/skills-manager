"""测试 MCP 配置中心模块。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skills_manager.mcp_config import (
    MCPConfigError,
    MCPConfigManager,
    MCPServer,
    builtin_profiles,
    load_servers,
    save_servers,
)


# ── MCPServer ─────────────────────────────────────────────


class TestMCPServer:
    def test_from_dict_minimal(self):
        s = MCPServer.from_dict("foo", {"command": "python"})
        assert s.name == "foo"
        assert s.command == "python"
        assert s.args == []
        assert s.env == {}
        assert s.disabled is False

    def test_from_dict_full(self):
        s = MCPServer.from_dict(
            "foo",
            {
                "command": "python",
                "args": ["-m", "x"],
                "env": {"A": "1"},
                "disabled": True,
                "transport": "stdio",
            },
        )
        assert s.args == ["-m", "x"]
        assert s.env == {"A": "1"}
        assert s.disabled is True
        # 未识别字段保留到 extra
        assert s.extra == {"transport": "stdio"}

    def test_from_dict_rejects_non_dict(self):
        with pytest.raises(MCPConfigError):
            MCPServer.from_dict("foo", "not a dict")  # type: ignore[arg-type]

    def test_to_dict_round_trip(self):
        original = {
            "command": "python",
            "args": ["x"],
            "env": {"A": "1"},
            "transport": "stdio",
        }
        s = MCPServer.from_dict("foo", original)
        result = s.to_dict()
        # extra 字段保留
        assert result["transport"] == "stdio"
        assert result["command"] == "python"
        # disabled=False 不应该写入
        assert "disabled" not in result

    def test_to_dict_omits_empty(self):
        s = MCPServer(name="foo", command="python")
        result = s.to_dict()
        assert result == {"command": "python"}


# ── load / save ───────────────────────────────────────────


class TestLoadSave:
    def test_load_missing_file(self, tmp_path):
        raw, servers = load_servers(tmp_path / "nope.json")
        assert raw == {}
        assert servers == {}

    def test_load_empty_file(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("", encoding="utf-8")
        raw, servers = load_servers(path)
        assert raw == {}
        assert servers == {}

    def test_load_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json}", encoding="utf-8")
        with pytest.raises(MCPConfigError):
            load_servers(path)

    def test_load_non_object_top_level(self, tmp_path):
        path = tmp_path / "arr.json"
        path.write_text("[]", encoding="utf-8")
        with pytest.raises(MCPConfigError):
            load_servers(path)

    def test_load_invalid_mcpservers_type(self, tmp_path):
        path = tmp_path / "x.json"
        path.write_text('{"mcpServers": "string"}', encoding="utf-8")
        with pytest.raises(MCPConfigError):
            load_servers(path)

    def test_save_creates_file(self, tmp_path):
        path = tmp_path / "cfg.json"
        servers = {"foo": MCPServer(name="foo", command="python")}
        save_servers(path, {}, servers)
        assert path.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["mcpServers"]["foo"]["command"] == "python"

    def test_save_preserves_other_keys(self, tmp_path):
        path = tmp_path / "cfg.json"
        raw = {"theme": "dark", "other": {"nested": 1}}
        servers = {"foo": MCPServer(name="foo", command="python")}
        save_servers(path, raw, servers)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["theme"] == "dark"
        assert data["other"] == {"nested": 1}
        assert "foo" in data["mcpServers"]

    def test_save_creates_backup(self, tmp_path):
        path = tmp_path / "cfg.json"
        path.write_text('{"mcpServers": {}}', encoding="utf-8")
        servers = {"x": MCPServer(name="x", command="cmd")}
        save_servers(path, {"mcpServers": {}}, servers)
        backup = path.with_suffix(path.suffix + ".bak")
        assert backup.is_file()


# ── MCPConfigManager ──────────────────────────────────────


@pytest.fixture
def tmp_config(tmp_path) -> Path:
    return tmp_path / "config.json"


@pytest.fixture
def manager(tmp_config) -> MCPConfigManager:
    mgr = MCPConfigManager(custom_paths={"test": tmp_config})
    return mgr


class TestMCPConfigManager:
    def test_builtin_profiles_present(self, manager):
        ids = {p.id for p in manager.profiles()}
        assert "claude-desktop" in ids
        assert "claude-code" in ids
        assert "cline" in ids
        assert "custom:test" in ids

    def test_resolve_path_custom(self, manager, tmp_config):
        assert manager.resolve_path("custom:test") == tmp_config

    def test_resolve_path_unknown_custom(self, manager):
        with pytest.raises(MCPConfigError):
            manager.resolve_path("custom:nope")

    def test_resolve_path_unknown_profile(self, manager):
        with pytest.raises(MCPConfigError):
            manager.resolve_path("bogus")

    def test_add_and_list(self, manager):
        server = MCPServer(name="foo", command="python", args=["-m", "x"])
        manager.add_or_update("custom:test", server)
        result = manager.list_servers("custom:test")
        assert len(result) == 1
        assert result[0].name == "foo"
        assert result[0].args == ["-m", "x"]

    def test_update_existing(self, manager):
        manager.add_or_update(
            "custom:test", MCPServer(name="foo", command="python")
        )
        manager.add_or_update(
            "custom:test", MCPServer(name="foo", command="node")
        )
        result = manager.list_servers("custom:test")
        assert len(result) == 1
        assert result[0].command == "node"

    def test_remove(self, manager):
        manager.add_or_update(
            "custom:test", MCPServer(name="foo", command="python")
        )
        assert manager.remove("custom:test", "foo") is True
        assert manager.list_servers("custom:test") == []

    def test_remove_missing(self, manager):
        assert manager.remove("custom:test", "nope") is False

    def test_set_disabled(self, manager):
        manager.add_or_update(
            "custom:test", MCPServer(name="foo", command="python")
        )
        assert manager.set_disabled("custom:test", "foo", True) is True
        s = manager.get_server("custom:test", "foo")
        assert s is not None
        assert s.disabled is True

    def test_set_disabled_missing(self, manager):
        assert manager.set_disabled("custom:test", "nope", True) is False

    def test_add_rejects_empty_name(self, manager):
        with pytest.raises(MCPConfigError):
            manager.add_or_update(
                "custom:test", MCPServer(name="", command="x")
            )

    def test_add_rejects_empty_command(self, manager):
        with pytest.raises(MCPConfigError):
            manager.add_or_update(
                "custom:test", MCPServer(name="foo", command="")
            )

    def test_add_custom_profile(self, tmp_path):
        mgr = MCPConfigManager()
        path = tmp_path / "new.json"
        prof = mgr.add_custom_profile("mine", path)
        assert prof.id == "custom:mine"
        assert mgr.resolve_path("custom:mine") == path

    def test_add_custom_profile_rejects_blank(self):
        mgr = MCPConfigManager()
        with pytest.raises(MCPConfigError):
            mgr.add_custom_profile("  ", Path("/x"))

    def test_install_skill(self, manager, tmp_path):
        skill_dir = tmp_path / "skills" / "translator"
        skill_dir.mkdir(parents=True)
        server = manager.install_skill_to(
            "custom:test",
            skill_name="translator",
            skill_path=skill_dir,
            python_executable="/usr/bin/python3",
            entry="server.py",
        )
        assert server.name == "translator"
        assert server.command == "/usr/bin/python3"
        assert server.args == [str(skill_dir / "server.py")]

    def test_install_skill_persisted(self, manager, tmp_path, tmp_config):
        skill_dir = tmp_path / "skills" / "x"
        skill_dir.mkdir(parents=True)
        manager.install_skill_to(
            "custom:test", skill_name="x", skill_path=skill_dir
        )
        data = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert "x" in data["mcpServers"]
        assert str(skill_dir / "server.py") in data["mcpServers"]["x"]["args"][0]


def test_builtin_profiles_have_required_fields():
    for prof in builtin_profiles():
        assert prof.id
        assert prof.label
        # default_path 在某些平台可能为 None（如 Linux 上的 Claude Desktop），
        # 但 id 和 label 必须存在
