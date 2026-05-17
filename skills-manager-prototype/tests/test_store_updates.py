"""测试 store 的批量卸载 / 检查更新 / 一键更新。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from skills_manager.store import Store


@pytest.fixture
def store(tmp_path) -> Store:
    return Store(base_dir=tmp_path / ".skills")


def _make_source(parent: Path, name: str, version: str = "1.0.0") -> Path:
    d = parent / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"""---
name: {name}
version: "{version}"
description: A test skill
summary: For testing
tags: [test]
category: misc
---

## 功能

Test function.

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| input | string | ✅ | Input text |
""",
        encoding="utf-8",
    )
    return d


class TestUninstallMany:
    def test_uninstall_many(self, store, tmp_path):
        a = _make_source(tmp_path / "srcs", "alpha")
        b = _make_source(tmp_path / "srcs", "beta")
        store.install(a)
        store.install(b)
        ok, failed = store.uninstall_many(["alpha", "beta"])
        assert set(ok) == {"alpha", "beta"}
        assert failed == []
        assert store.list_all() == []

    def test_uninstall_many_partial(self, store, tmp_path):
        a = _make_source(tmp_path / "srcs", "only")
        store.install(a)
        ok, failed = store.uninstall_many(["only", "ghost"])
        assert "only" in ok
        # 'ghost' 不存在但 uninstall() 本身不抛错；ok/failed 都可以接受
        names = set(ok) | {n for n, _ in failed}
        assert "ghost" in names


class TestCheckOutdated:
    def test_local_newer_marks_updatable(self, store, tmp_path):
        src = _make_source(tmp_path / "srcs", "alpha", "1.0.0")
        store.install(src)
        md = src / "SKILL.md"
        md.write_text(md.read_text(encoding="utf-8").replace("1.0.0", "2.0.0"), encoding="utf-8")
        entries = store.check_outdated()
        e = next(e for e in entries if e["name"] == "alpha")
        assert e["updatable"] is True
        assert e["latest_version"] == "2.0.0"

    def test_up_to_date(self, store, tmp_path):
        src = _make_source(tmp_path / "srcs", "fresh", "1.0.0")
        store.install(src)
        e = next(e for e in store.check_outdated() if e["name"] == "fresh")
        assert e["updatable"] is False
        assert e["reason"] == "已是最新"

    def test_remote_marked(self, store, tmp_path):
        src = _make_source(tmp_path / "srcs", "remote-skill", "1.0.0")
        store.install(src)
        idx = store._load_index()
        idx["skills"]["remote-skill"]["source"] = "https://example.com/x.skill"
        store._save_index(idx)
        e = next(e for e in store.check_outdated() if e["name"] == "remote-skill")
        assert e["updatable"] is True
        assert e["reason"] == "remote"

    def test_source_missing(self, store, tmp_path):
        src = _make_source(tmp_path / "srcs", "ghost-source", "1.0.0")
        store.install(src)
        shutil.rmtree(src)
        e = next(e for e in store.check_outdated() if e["name"] == "ghost-source")
        assert e["updatable"] is False
        assert "不存在" in e["reason"]


class TestUpdateAll:
    def test_runs_only_updatable(self, store, tmp_path):
        # 需要更新的
        a = _make_source(tmp_path / "srcs", "needs-update", "1.0.0")
        store.install(a)
        md = a / "SKILL.md"
        md.write_text(md.read_text(encoding="utf-8").replace("1.0.0", "1.1.0"), encoding="utf-8")
        # 不需要更新的
        b = _make_source(tmp_path / "srcs", "fresh", "1.0.0")
        store.install(b)

        ok, failed = store.update_all()
        assert "needs-update" in ok
        assert "fresh" not in ok
        assert failed == []
        assert store.get("needs-update").version == "1.1.0"
        assert store.get("fresh").version == "1.0.0"
