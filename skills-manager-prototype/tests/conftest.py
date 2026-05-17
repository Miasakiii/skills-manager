"""测试夹具。

关键：使 ``Store.install`` 在测试中不再触碰用户真实的 ~/.claude/skills 等目录。
默认的 ``_AgentSync.get_agent_skills_dirs()`` 会扫描多个 home 子目录并把
临时 skill 复制 / symlink 过去，过去的测试遗留了大量污染。autouse 打桩后
所有测试都安全。
"""

from __future__ import annotations

import pytest

from skills_manager.store.agent_sync import _AgentSync


@pytest.fixture(autouse=True)
def _no_agent_sync(monkeypatch):
    """禁止 Store 把测试 skill 同步到真实 agent 目录。"""
    monkeypatch.setattr(_AgentSync, "get_agent_skills_dirs", staticmethod(lambda: []))
    yield
