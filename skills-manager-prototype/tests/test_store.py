"""测试本地存储管理。"""

import json
from pathlib import Path

import pytest

from skills_manager.parser import parse_skill_md
from skills_manager.store import Store, StoreError


@pytest.fixture
def store(tmp_path) -> Store:
    """创建临时 Store 实例。"""
    return Store(base_dir=tmp_path / ".skills")


@pytest.fixture
def sample_skill_dir(tmp_path) -> Path:
    """创建一个示例 Skill 目录。"""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: test-skill
version: "1.0.0"
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
    (skill_dir / "handler.py").write_text("def run(input): return input", encoding="utf-8")
    return skill_dir


class TestStoreInstall:
    def test_install_basic(self, store, sample_skill_dir):
        result = store.install(sample_skill_dir)
        assert result.name == "test-skill"
        assert result.version == "1.0.0"
        assert (store.store_dir / "test-skill" / "SKILL.md").exists()

    def test_install_with_custom_name(self, store, sample_skill_dir):
        result = store.install(sample_skill_dir, name="custom-name")
        assert result.name == "custom-name"
        assert (store.store_dir / "custom-name" / "SKILL.md").exists()

    def test_install_no_skill_md(self, store, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(StoreError, match="No SKILL.md"):
            store.install(empty_dir)

    def test_install_force_overwrite(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        # 再次安装，不 force 应该报错
        with pytest.raises(StoreError, match="already installed"):
            store.install(sample_skill_dir)
        # force 应该成功
        result = store.install(sample_skill_dir, force=True)
        assert result.name == "test-skill"


class TestStoreUninstall:
    def test_uninstall(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        store.uninstall("test-skill")
        assert not (store.store_dir / "test-skill").exists()
        assert not store.exists("test-skill")

    def test_uninstall_nonexistent(self, store):
        # 不应报错
        store.uninstall("nonexistent")


class TestStoreQuery:
    def test_list_empty(self, store):
        assert store.list_all() == []

    def test_list_after_install(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        skills = store.list_all()
        assert len(skills) == 1
        assert skills[0].name == "test-skill"

    def test_get_existing(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        skill = store.get("test-skill")
        assert skill.name == "test-skill"
        assert skill.version == "1.0.0"

    def test_get_nonexistent(self, store):
        with pytest.raises(StoreError, match="not found"):
            store.get("nonexistent")

    def test_exists(self, store, sample_skill_dir):
        assert not store.exists("test-skill")
        store.install(sample_skill_dir)
        assert store.exists("test-skill")


class TestStoreSearch:
    def test_search_by_name(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        results = store.search("test")
        assert len(results) == 1

    def test_search_by_description(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        results = store.search("testing")
        assert len(results) == 1

    def test_search_no_match(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        results = store.search("nonexistent")
        assert len(results) == 0

    def test_search_by_category(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        results = store.search("", category="misc")
        assert len(results) == 1
        results = store.search("", category="language")
        assert len(results) == 0

    def test_search_by_tag(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        results = store.search("", tag="test")
        assert len(results) == 1
        results = store.search("", tag="nonexistent")
        assert len(results) == 0


class TestStoreSkillMd:
    def test_get_skill_md_path(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        path = store.get_skill_md_path("test-skill")
        assert path.exists()
        assert path.name == "SKILL.md"

    def test_get_skill_content(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        content = store.get_skill_content("test-skill")
        assert "name: test-skill" in content

    def test_get_skill_ir(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        ir = store.get_skill_ir("test-skill")
        assert ir.name == "test-skill"
        assert len(ir.parameters) == 1
