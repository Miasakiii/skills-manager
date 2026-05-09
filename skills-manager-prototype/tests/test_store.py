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
        with pytest.raises(StoreError, match="验证失败"):
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

    def test_get_skill_content_nonexistent(self, store):
        with pytest.raises(StoreError, match="SKILL.md not found"):
            store.get_skill_content("nonexistent")

    def test_get_skill_ir(self, store, sample_skill_dir):
        store.install(sample_skill_dir)
        ir = store.get_skill_ir("test-skill")
        assert ir.name == "test-skill"
        assert len(ir.parameters) == 1

    def test_get_skill_ir_nonexistent(self, store):
        with pytest.raises(StoreError, match="SKILL.md not found"):
            store.get_skill_ir("nonexistent")


class TestStoreInstallFromPackage:
    def test_install_from_package(self, store, sample_skill_dir, tmp_path):
        """测试从 .skill 包安装。"""
        from skills_manager.packager import pack

        # 先打包
        packed = pack(sample_skill_dir, tmp_path)
        assert packed.exists()

        # 从包安装
        result = store.install_from_package(packed)
        assert result.name == "test-skill"
        assert store.exists("test-skill")

    def test_install_from_package_nonexistent(self, store, tmp_path):
        """测试安装不存在的包。"""
        with pytest.raises(StoreError, match="Package not found"):
            store.install_from_package(tmp_path / "nonexistent.skill")


class TestStoreDiscover:
    def test_discover_in_paths(self, store, sample_skill_dir, tmp_path):
        """测试自动发现功能。"""
        # 创建扫描目录
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()

        # 复制 skill 到扫描目录
        import shutil
        dest = scan_dir / "my-skill"
        shutil.copytree(sample_skill_dir, dest)

        # 发现
        discovered = store.discover_in_paths([scan_dir])
        assert len(discovered) == 1
        assert discovered[0].name == "my-skill"

    def test_discover_excludes_installed(self, store, sample_skill_dir, tmp_path):
        """测试排除已安装的 skill。"""
        # 先安装
        store.install(sample_skill_dir)

        # 创建扫描目录
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()
        import shutil
        dest = scan_dir / "test-skill"
        shutil.copytree(sample_skill_dir, dest)

        # 发现（应该为空，因为已安装）
        discovered = store.discover_in_paths([scan_dir])
        assert len(discovered) == 0

    def test_discover_nonexistent_path(self, store, tmp_path):
        """测试不存在的扫描路径。"""
        discovered = store.discover_in_paths([tmp_path / "nonexistent"])
        assert len(discovered) == 0


class TestStoreScan:
    def test_scan_directory(self, store, tmp_path):
        """测试扫描目录功能。"""
        import shutil
        # 创建独立的扫描目录
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()

        # 创建多个 skill 目录
        for i in range(3):
            skill_dir = scan_dir / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i}\nversion: 1.0.0\ndescription: Test\n---\n",
                encoding="utf-8",
            )

        # 扫描
        results = store.scan_directory(scan_dir)
        assert len(results) == 3

    def test_scan_directory_recursive(self, store, tmp_path):
        """测试递归扫描。"""
        # 创建独立的扫描目录
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()

        # 创建嵌套结构
        subdir = scan_dir / "subdir"
        subdir.mkdir()
        nested = subdir / "nested-skill"
        nested.mkdir()
        (nested / "SKILL.md").write_text(
            "---\nname: nested-skill\nversion: 1.0.0\ndescription: Test\n---\n",
            encoding="utf-8",
        )

        results = store.scan_directory(scan_dir)
        assert len(results) == 1
        assert results[0].name == "nested-skill"

    def test_scan_and_install(self, store, tmp_path):
        """测试批量扫描安装。"""
        # 创建独立的扫描目录
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()

        # 创建多个 skill
        for i in range(2):
            skill_dir = scan_dir / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i}\nversion: 1.0.0\ndescription: Test\n---\n",
                encoding="utf-8",
            )

        installed, failed = store.scan_and_install(scan_dir)
        assert len(installed) == 2
        assert len(failed) == 0
        assert store.exists("skill-0")
        assert store.exists("skill-1")


class TestStoreWatchPaths:
    def test_get_watch_paths_empty(self, store):
        """测试获取空监视路径列表。"""
        paths = store.get_watch_paths()
        assert paths == []

    def test_add_watch_path(self, store):
        """测试添加监视路径。"""
        store.add_watch_path("/path/to/skills")
        paths = store.get_watch_paths()
        assert "/path/to/skills" in paths

    def test_add_watch_path_duplicate(self, store):
        """测试添加重复监视路径。"""
        store.add_watch_path("/path/to/skills")
        store.add_watch_path("/path/to/skills")
        paths = store.get_watch_paths()
        assert paths.count("/path/to/skills") == 1

    def test_remove_watch_path(self, store):
        """测试移除监视路径。"""
        store.add_watch_path("/path/to/skills")
        store.remove_watch_path("/path/to/skills")
        paths = store.get_watch_paths()
        assert "/path/to/skills" not in paths

    def test_remove_watch_path_nonexistent(self, store):
        """测试移除不存在的监视路径。"""
        store.remove_watch_path("/nonexistent")
        # 不应报错


class TestStoreSearchSkillType:
    def test_search_by_skill_type(self, store, sample_skill_dir, tmp_path):
        """测试按 skill_type 搜索。"""
        # 创建带 skill_type 的 skill
        skill_dir = tmp_path / "typed-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """---
name: typed-skill
version: "1.0.0"
description: A typed skill
skill_type: component
---
## 功能
Test.
""",
            encoding="utf-8",
        )
        store.install(skill_dir)

        # 搜索
        results = store.search("", skill_type="component")
        assert len(results) == 1
        assert results[0].name == "typed-skill"

        results = store.search("", skill_type="workflow")
        assert len(results) == 0
