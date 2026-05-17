"""MCP 客户端配置中心。

读写主流 MCP 客户端的 ``mcpServers`` 配置：

- Claude Desktop：``claude_desktop_config.json``
- Claude Code：``~/.claude.json``
- Cline（VS Code 扩展）：``cline_mcp_settings.json``
- 自定义路径：任意 JSON 文件

设计原则：

1. 不修改用户文件之外的内容，写入时保留未识别的顶级字段；
2. 写入前若文件存在则备份为 ``<name>.bak``；
3. 所有读写都通过路径白名单校验，避免误操作；
4. 不主动启动 / 停止任何 MCP 进程，仅做配置管理。
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .logging import get_logger

logger = get_logger(__name__)


class MCPConfigError(Exception):
    """MCP 配置操作错误。"""


@dataclass
class MCPServer:
    """单个 MCP Server 配置。

    遵循 Claude Desktop / Cline 通用结构：

    ```json
    {
      "command": "python",
      "args": ["-m", "skills_manager.server", "--mode", "mcp"],
      "env": {"FOO": "bar"}
    }
    ```
    """

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    disabled: bool = False
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, name: str, data: dict) -> MCPServer:
        if not isinstance(data, dict):
            raise MCPConfigError(f"server '{name}' 配置必须是对象")
        known = {"command", "args", "env", "disabled"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            name=name,
            command=str(data.get("command", "")),
            args=list(data.get("args", []) or []),
            env=dict(data.get("env", {}) or {}),
            disabled=bool(data.get("disabled", False)),
            extra=extra,
        )

    def to_dict(self) -> dict:
        result: dict = {"command": self.command}
        if self.args:
            result["args"] = list(self.args)
        if self.env:
            result["env"] = dict(self.env)
        if self.disabled:
            result["disabled"] = True
        # 保留未识别字段
        for k, v in self.extra.items():
            result.setdefault(k, v)
        return result


@dataclass
class MCPClientProfile:
    """MCP 客户端 profile：标识 + 默认配置文件路径。"""

    id: str
    label: str
    default_path: Path | None
    description: str = ""

    @property
    def exists(self) -> bool:
        return self.default_path is not None and self.default_path.is_file()


def _appdata_dir() -> Path | None:
    """返回 Windows %APPDATA%。"""
    val = os.environ.get("APPDATA")
    return Path(val) if val else None


def _claude_desktop_config_path() -> Path | None:
    """返回 Claude Desktop 配置文件的默认路径（不存在时仍返回，便于新建）。"""
    if sys.platform == "win32":
        base = _appdata_dir()
        if base is None:
            return None
        return base / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    # Linux 暂无官方 Desktop 版，使用 XDG_CONFIG_HOME 兜底
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "Claude" / "claude_desktop_config.json"


def _claude_code_config_path() -> Path:
    """Claude Code 配置（~/.claude.json）。"""
    return Path.home() / ".claude.json"


def _cline_config_path() -> Path | None:
    """Cline（VS Code 扩展）的 ``cline_mcp_settings.json``。

    路径随操作系统不同，扩展安装后位于：
    Windows: %APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
    macOS:   ~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
    Linux:   ~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
    """
    rel = Path(
        "User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
    )
    if sys.platform == "win32":
        base = _appdata_dir()
        if base is None:
            return None
        return base / "Code" / rel
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / rel
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "Code" / rel


# ── 内置 profile 表 ───────────────────────────────────────────


def builtin_profiles() -> list[MCPClientProfile]:
    """返回内置 MCP 客户端 profile（路径基于当前用户环境）。"""
    return [
        MCPClientProfile(
            id="claude-desktop",
            label="Claude Desktop",
            default_path=_claude_desktop_config_path(),
            description="桌面版 Claude（claude_desktop_config.json）",
        ),
        MCPClientProfile(
            id="claude-code",
            label="Claude Code",
            default_path=_claude_code_config_path(),
            description="Claude Code CLI（~/.claude.json）",
        ),
        MCPClientProfile(
            id="cline",
            label="Cline (VS Code)",
            default_path=_cline_config_path(),
            description="Cline VS Code 扩展（globalStorage 下的 cline_mcp_settings.json）",
        ),
    ]


def get_profile(profile_id: str) -> MCPClientProfile | None:
    """按 id 取内置 profile。"""
    for p in builtin_profiles():
        if p.id == profile_id:
            return p
    return None


# ── 配置文件读写 ──────────────────────────────────────────────


def _safe_load_json(path: Path) -> dict:
    """读取 JSON 文件；不存在或为空时返回 {}。"""
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise MCPConfigError(f"读取 {path} 失败: {e}") from e
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise MCPConfigError(f"{path} 不是合法 JSON: {e}") from e
    if not isinstance(data, dict):
        raise MCPConfigError(f"{path} 顶层必须是 JSON 对象")
    return data


def _atomic_write_json(path: Path, data: dict) -> None:
    """原子写入 JSON：写临时文件再 replace。失败时尝试恢复 ``.bak``。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_suffix(path.suffix + ".bak")
    if path.is_file():
        try:
            shutil.copy2(path, backup)
        except OSError:
            logger.warning("无法备份 %s 到 %s", path, backup)

    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        if backup.is_file():
            try:
                shutil.copy2(backup, path)
            except OSError:
                pass
        if tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise MCPConfigError(f"写入 {path} 失败: {e}") from e


def load_servers(path: Path) -> tuple[dict, dict[str, MCPServer]]:
    """读取配置文件，返回 ``(原始 JSON, mcpServers dict)``。

    配置文件中若没有 ``mcpServers`` 字段，返回空字典。原始 JSON 在写回时
    用于保留其他顶级字段。
    """
    raw = _safe_load_json(path)
    servers_raw = raw.get("mcpServers") or {}
    if not isinstance(servers_raw, dict):
        raise MCPConfigError(f"{path} 的 mcpServers 必须是对象")
    servers = {
        name: MCPServer.from_dict(name, data) for name, data in servers_raw.items()
    }
    return raw, servers


def save_servers(path: Path, raw: dict, servers: dict[str, MCPServer]) -> None:
    """把 servers 写回到配置文件，保留原始 JSON 中的其他字段。"""
    data = copy.deepcopy(raw) if raw else {}
    data["mcpServers"] = {name: s.to_dict() for name, s in servers.items()}
    _atomic_write_json(path, data)


# ── MCPConfigManager：业务入口 ────────────────────────────────


class MCPConfigManager:
    """对外的 MCP 配置中心入口。

    用法::

        mgr = MCPConfigManager()
        for prof in mgr.profiles():
            ...
        servers = mgr.list_servers("claude-desktop")
        mgr.add_or_update("claude-desktop", server)
        mgr.remove("claude-desktop", "translator")
    """

    def __init__(self, custom_paths: dict[str, Path] | None = None):
        self._custom_paths: dict[str, Path] = dict(custom_paths or {})

    # -- profiles -------------------------------------------------

    def profiles(self) -> list[MCPClientProfile]:
        """返回所有可用 profile（内置 + 自定义）。"""
        items = list(builtin_profiles())
        for cid, path in self._custom_paths.items():
            items.append(
                MCPClientProfile(
                    id=f"custom:{cid}",
                    label=cid,
                    default_path=path,
                    description=f"自定义配置: {path}",
                )
            )
        return items

    def add_custom_profile(self, label: str, path: Path) -> MCPClientProfile:
        """注册一个自定义 profile。``label`` 用于显示，``path`` 必须是 JSON 文件。"""
        label = label.strip()
        if not label:
            raise MCPConfigError("自定义 profile 名称不能为空")
        if path.exists() and not path.is_file():
            raise MCPConfigError(f"路径 {path} 不是文件")
        self._custom_paths[label] = path
        return MCPClientProfile(
            id=f"custom:{label}",
            label=label,
            default_path=path,
            description=f"自定义配置: {path}",
        )

    def resolve_path(self, profile_id: str) -> Path:
        """根据 profile id 取出对应的 JSON 文件路径。"""
        if profile_id.startswith("custom:"):
            label = profile_id[len("custom:") :]
            if label not in self._custom_paths:
                raise MCPConfigError(f"未注册的自定义 profile: {label}")
            return self._custom_paths[label]
        prof = get_profile(profile_id)
        if prof is None:
            raise MCPConfigError(f"未知 profile: {profile_id}")
        if prof.default_path is None:
            raise MCPConfigError(f"{prof.label} 在当前平台不可用")
        return prof.default_path

    # -- server CRUD ---------------------------------------------

    def list_servers(self, profile_id: str) -> list[MCPServer]:
        path = self.resolve_path(profile_id)
        _, servers = load_servers(path)
        return list(servers.values())

    def get_server(self, profile_id: str, name: str) -> MCPServer | None:
        path = self.resolve_path(profile_id)
        _, servers = load_servers(path)
        return servers.get(name)

    def add_or_update(self, profile_id: str, server: MCPServer) -> None:
        if not server.name:
            raise MCPConfigError("MCP server 名称不能为空")
        if not server.command:
            raise MCPConfigError("MCP server 必须指定 command")
        path = self.resolve_path(profile_id)
        raw, servers = load_servers(path)
        servers[server.name] = server
        save_servers(path, raw, servers)
        logger.info("MCP server %s 已写入 %s", server.name, path)

    def remove(self, profile_id: str, name: str) -> bool:
        path = self.resolve_path(profile_id)
        raw, servers = load_servers(path)
        if name not in servers:
            return False
        del servers[name]
        save_servers(path, raw, servers)
        logger.info("MCP server %s 已从 %s 移除", name, path)
        return True

    def set_disabled(self, profile_id: str, name: str, disabled: bool) -> bool:
        path = self.resolve_path(profile_id)
        raw, servers = load_servers(path)
        if name not in servers:
            return False
        servers[name].disabled = disabled
        save_servers(path, raw, servers)
        return True

    # -- 与 Skill 集成 -------------------------------------------

    @staticmethod
    def skill_to_server(
        skill_name: str,
        skill_path: Path,
        python_executable: str | None = None,
        entry: str = "server.py",
    ) -> MCPServer:
        """根据已安装的 skill 生成默认的 MCP server 配置。

        生成约定：

        - command：当前 Python 解释器
        - args：``["<skill_path>/<entry>"]``（若文件不存在，仍写入路径以便用户后续放置 server.py）
        - env：空

        Args:
            skill_name: skill 名称，作为 MCP server name。
            skill_path: skill 安装目录。
            python_executable: 覆盖默认的 ``sys.executable``。
            entry: 入口文件名，默认 ``server.py``。
        """
        cmd = python_executable or sys.executable or "python"
        entry_path = skill_path / entry
        return MCPServer(
            name=skill_name,
            command=cmd,
            args=[str(entry_path)],
            env={},
        )

    def install_skill_to(
        self,
        profile_id: str,
        skill_name: str,
        skill_path: Path,
        python_executable: str | None = None,
        entry: str = "server.py",
    ) -> MCPServer:
        """把 skill 配置写入指定 profile 的 mcpServers。

        返回写入的 MCPServer，便于调用方展示。
        """
        server = self.skill_to_server(
            skill_name, skill_path, python_executable=python_executable, entry=entry
        )
        self.add_or_update(profile_id, server)
        return server
