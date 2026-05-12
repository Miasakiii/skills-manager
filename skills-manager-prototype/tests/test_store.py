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
        with pytest.raises(StoreError, match="Validation failed"):
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
        store.install(sample_skill_dir, translate=False)
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


class TestStoreScanWithInfo:
    """扫描目录返回详细信息测试。"""

    def test_scan_with_info_basic(self, store, tmp_path):
        """测试基本扫描信息。"""
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()

        skill_dir = scan_dir / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\nversion: 1.0.0\ndescription: Test\n---\n",
            encoding="utf-8",
        )

        results = store.scan_directory_with_info(scan_dir)
        assert len(results) == 1
        assert results[0]["name"] == "my-skill"
        assert results[0]["version"] == "1.0.0"
        assert results[0]["installed"] is False

    def test_scan_with_info_installed(self, store, sample_skill_dir, tmp_path):
        """测试已安装标记。"""
        # 先安装
        store.install(sample_skill_dir)

        # 扫描包含同名 skill 的目录
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()
        import shutil
        dest = scan_dir / "test-skill"
        shutil.copytree(sample_skill_dir, dest)

        results = store.scan_directory_with_info(scan_dir)
        assert len(results) == 1
        assert results[0]["name"] == "test-skill"
        assert results[0]["installed"] is True

    def test_scan_with_info_empty(self, store, tmp_path):
        """测试空目录。"""
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()

        results = store.scan_directory_with_info(scan_dir)
        assert len(results) == 0

    def test_scan_with_info_multiple(self, store, tmp_path):
        """测试多个 Skill。"""
        scan_dir = tmp_path / "scan"
        scan_dir.mkdir()

        for i in range(3):
            skill_dir = scan_dir / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i}\nversion: 1.0.0\ndescription: Test {i}\n---\n",
                encoding="utf-8",
            )

        results = store.scan_directory_with_info(scan_dir)
        assert len(results) == 3
        assert all(r["installed"] is False for r in results)


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


class TestStoreVersionHistory:
    """版本历史测试。"""

    def test_version_history_empty(self, store, sample_skill_dir):
        """测试空版本历史。"""
        store.install(sample_skill_dir)
        history = store.get_version_history("test-skill")
        assert len(history) == 1  # 安装时会记录一次

    def test_version_history_after_install(self, store, sample_skill_dir):
        """测试安装后版本历史。"""
        store.install(sample_skill_dir)
        history = store.get_version_history("test-skill")
        assert len(history) == 1
        assert history[0]["version"] == "1.0.0"

    def test_version_history_after_upgrade(self, store, sample_skill_dir, tmp_path):
        """测试升级后版本历史。"""
        store.install(sample_skill_dir)

        # 创建新版本
        new_version_dir = tmp_path / "new-version"
        new_version_dir.mkdir()
        (new_version_dir / "SKILL.md").write_text(
            """---
name: test-skill
version: "2.0.0"
description: Updated test skill
summary: For testing
tags: [test]
category: misc
---

## 功能

Updated test function.

## 参数

| 参数 | 类型 | 必需 | 说明 |
| --- | --- | --- | --- |
| input | string | ✅ | Input text |
""",
            encoding="utf-8",
        )
        (new_version_dir / "handler.py").write_text("def run(input): return input", encoding="utf-8")

        # 升级
        store.upgrade("test-skill", new_version_dir)

        history = store.get_version_history("test-skill")
        # 安装记录 + 备份快照 + 升级记录 = 3 条
        assert len(history) == 3
        assert history[0]["version"] == "1.0.0"  # 安装记录
        assert history[1]["version"] == "1.0.0"  # 备份快照
        assert history[2]["version"] == "2.0.0"  # 升级记录


class TestStoreUpgrade:
    """升级功能测试。"""

    def test_upgrade_basic(self, store, sample_skill_dir, tmp_path):
        """测试基本升级。"""
        store.install(sample_skill_dir)

        # 创建新版本
        new_version_dir = tmp_path / "new-version"
        new_version_dir.mkdir()
        (new_version_dir / "SKILL.md").write_text(
            """---
name: test-skill
version: "2.0.0"
description: Updated test skill
summary: For testing
tags: [test]
category: misc
---

## 功能

Updated test function.

## 参数

| 参数 | 类型 | 必需 | 说明 |
| --- | --- | --- | --- |
| input | string | ✅ | Input text |
""",
            encoding="utf-8",
        )
        (new_version_dir / "handler.py").write_text("def run(input): return input", encoding="utf-8")

        # 升级
        result = store.upgrade("test-skill", new_version_dir)
        assert result.version == "2.0.0"
        assert store.exists("test-skill")

    def test_upgrade_nonexistent(self, store, tmp_path):
        """测试升级不存在的 skill。"""
        new_version_dir = tmp_path / "new-version"
        new_version_dir.mkdir()
        (new_version_dir / "SKILL.md").write_text(
            "---\nname: test\nversion: 1.0.0\ndescription: Test\n---\n",
            encoding="utf-8",
        )

        with pytest.raises(StoreError, match="not installed"):
            store.upgrade("nonexistent", new_version_dir)


class TestStoreRollback:
    """回滚功能测试。"""

    def test_rollback_to_previous(self, store, sample_skill_dir, tmp_path):
        """测试回滚到上一个版本。"""
        # 安装 v1
        store.install(sample_skill_dir)

        # 创建并升级到 v2
        new_version_dir = tmp_path / "v2"
        new_version_dir.mkdir()
        (new_version_dir / "SKILL.md").write_text(
            """---
name: test-skill
version: "2.0.0"
description: V2
summary: V2
tags: [test]
category: misc
---

## 功能

V2.

## 参数

| 参数 | 类型 | 必需 | 说明 |
| --- | --- | --- | --- |
| input | string | ✅ | Input text |
""",
            encoding="utf-8",
        )
        store.upgrade("test-skill", new_version_dir)

        # 回滚
        result = store.rollback("test-skill")
        assert result.version == "1.0.0"

    def test_rollback_to_specific_version(self, store, sample_skill_dir, tmp_path):
        """测试回滚到指定版本。"""
        # 安装 v1
        store.install(sample_skill_dir)

        # 升级到 v2
        v2_dir = tmp_path / "v2"
        v2_dir.mkdir()
        (v2_dir / "SKILL.md").write_text(
            "---\nname: test-skill\nversion: 2.0.0\ndescription: V2\n---\n",
            encoding="utf-8",
        )
        store.upgrade("test-skill", v2_dir)

        # 升级到 v3
        v3_dir = tmp_path / "v3"
        v3_dir.mkdir()
        (v3_dir / "SKILL.md").write_text(
            "---\nname: test-skill\nversion: 3.0.0\ndescription: V3\n---\n",
            encoding="utf-8",
        )
        store.upgrade("test-skill", v3_dir)

        # 回滚到 v1
        result = store.rollback("test-skill", "1.0.0")
        assert result.version == "1.0.0"

    def test_rollback_nonexistent(self, store):
        """测试回滚不存在的 skill。"""
        with pytest.raises(StoreError, match="not installed"):
            store.rollback("nonexistent")

    def test_rollback_no_history(self, store, sample_skill_dir):
        """测试无历史时回滚。"""
        store.install(sample_skill_dir)
        # 清空历史
        store._save_version_history("test-skill", [])

        with pytest.raises(StoreError, match="No version history"):
            store.rollback("test-skill")


class TestStoreUpdate:
    """更新功能测试。"""

    def test_update_from_local_dir(self, store, sample_skill_dir):
        """测试从本地目录更新。"""
        store.install(sample_skill_dir)
        # 修改版本号
        skill_md = sample_skill_dir / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        skill_md.write_text(content.replace("1.0.0", "2.0.0"), encoding="utf-8")
        result = store.update("test-skill")
        assert result.version == "2.0.0"

    def test_update_nonexistent(self, store):
        """测试更新不存在的 skill。"""
        with pytest.raises(StoreError, match="not found"):
            store.update("nonexistent")

    def test_update_no_source(self, store, sample_skill_dir):
        """测试无来源信息时更新。"""
        store.install(sample_skill_dir)
        # 清空来源信息
        index = store._load_index()
        index["skills"]["test-skill"]["source"] = ""
        store._save_index(index)
        with pytest.raises(StoreError, match="has no source information"):
            store.update("test-skill")

    def test_update_source_not_exist(self, store, sample_skill_dir, tmp_path):
        """测试来源目录不存在时更新。"""
        store.install(sample_skill_dir)
        # 修改来源为不存在的路径
        index = store._load_index()
        index["skills"]["test-skill"]["source"] = str(tmp_path / "nonexistent")
        store._save_index(index)
        with pytest.raises(StoreError, match="Source directory does not exist"):
            store.update("test-skill")

    def test_can_update(self, store, sample_skill_dir):
        """测试检查是否可更新。"""
        store.install(sample_skill_dir)
        can, reason = store.can_update("test-skill")
        assert can is True
        assert "来源" in reason

    def test_can_update_no_source(self, store, sample_skill_dir):
        """测试无来源时检查更新。"""
        store.install(sample_skill_dir)
        index = store._load_index()
        index["skills"]["test-skill"]["source"] = ""
        store._save_index(index)
        can, reason = store.can_update("test-skill")
        assert can is False
        assert "No source information" in reason

    def test_can_update_nonexistent(self, store):
        """测试不存在的 skill 检查更新。"""
        can, reason = store.can_update("nonexistent")
        assert can is False


class TestStoreExportHistory:
    """导出历史记录测试。"""

    def test_get_export_history_empty(self, store):
        """测试空导出历史。"""
        history = store.get_export_history()
        assert history == []

    def test_add_export_history(self, store):
        """测试添加导出历史。"""
        store.add_export_history("translator", "openai", "/tmp/output.json")
        history = store.get_export_history()
        assert len(history) == 1
        assert history[0]["skill_name"] == "translator"
        assert history[0]["format"] == "openai"
        assert history[0]["output_path"] == "/tmp/output.json"

    def test_add_multiple_export_history(self, store):
        """测试添加多条导出历史。"""
        store.add_export_history("translator", "openai", "/tmp/1.json")
        store.add_export_history("code-reviewer", "claude", "/tmp/2.json")
        history = store.get_export_history()
        assert len(history) == 2
        assert history[0]["skill_name"] == "translator"
        assert history[1]["skill_name"] == "code-reviewer"

    def test_clear_export_history(self, store):
        """测试清空导出历史。"""
        store.add_export_history("translator", "openai", "/tmp/1.json")
        store.clear_export_history()
        history = store.get_export_history()
        assert history == []

    def test_export_history_limit(self, store):
        """测试导出历史记录数量限制。"""
        for i in range(105):
            store.add_export_history(f"skill-{i}", "openai", f"/tmp/{i}.json")
        history = store.get_export_history()
        assert len(history) == 100
        # 应该保留最后 100 条
        assert history[0]["skill_name"] == "skill-5"
        assert history[-1]["skill_name"] == "skill-104"


class TestStoreInstallFromUrl:
    """从 URL 安装测试。"""

    def test_install_from_url_no_httpx(self, store, monkeypatch):
        """测试 httpx 未安装时的错误处理。"""
        # 模拟 httpx 未安装
        import sys
        monkeypatch.setitem(sys.modules, "httpx", None)

        with pytest.raises(StoreError, match="需要安装 httpx"):
            store.install_from_url("https://example.com/skill.skill")


class TestStoreProfiles:
    """Profile 管理测试。"""

    def test_get_profiles_empty(self, store):
        """测试空 Profile 列表。"""
        profiles = store.get_profiles()
        assert profiles == []

    def test_create_profile(self, store):
        """测试创建 Profile。"""
        profile = store.create_profile("my-profile", "测试 Profile")
        assert profile["name"] == "my-profile"
        assert profile["description"] == "测试 Profile"
        assert profile["skills"] == []

    def test_create_profile_with_skills(self, store):
        """测试创建带 Skill 的 Profile。"""
        profile = store.create_profile(
            "my-profile",
            skills=["translator", "code-reviewer"],
        )
        assert profile["skills"] == ["translator", "code-reviewer"]

    def test_create_profile_duplicate(self, store):
        """测试创建重复 Profile。"""
        store.create_profile("my-profile")
        with pytest.raises(StoreError, match="already exists"):
            store.create_profile("my-profile")

    def test_get_profile(self, store):
        """测试获取单个 Profile。"""
        store.create_profile("my-profile", "测试")
        profile = store.get_profile("my-profile")
        assert profile["name"] == "my-profile"

    def test_get_profile_nonexistent(self, store):
        """测试获取不存在的 Profile。"""
        with pytest.raises(StoreError, match="not found"):
            store.get_profile("nonexistent")

    def test_update_profile(self, store):
        """测试更新 Profile。"""
        store.create_profile("my-profile")
        updated = store.update_profile("my-profile", description="新描述")
        assert updated["description"] == "新描述"

    def test_update_profile_skills(self, store):
        """测试更新 Profile 的 Skill 列表。"""
        store.create_profile("my-profile")
        updated = store.update_profile(
            "my-profile",
            skills=["translator", "code-reviewer"],
        )
        assert updated["skills"] == ["translator", "code-reviewer"]

    def test_delete_profile(self, store):
        """测试删除 Profile。"""
        store.create_profile("my-profile")
        store.delete_profile("my-profile")
        profiles = store.get_profiles()
        assert len(profiles) == 0

    def test_add_skill_to_profile(self, store):
        """测试向 Profile 添加 Skill。"""
        store.create_profile("my-profile")
        store.add_skill_to_profile("my-profile", "translator")
        profile = store.get_profile("my-profile")
        assert "translator" in profile["skills"]

    def test_add_skill_to_profile_duplicate(self, store):
        """测试向 Profile 添加重复 Skill。"""
        store.create_profile("my-profile", skills=["translator"])
        store.add_skill_to_profile("my-profile", "translator")
        profile = store.get_profile("my-profile")
        assert profile["skills"].count("translator") == 1

    def test_remove_skill_from_profile(self, store):
        """测试从 Profile 移除 Skill。"""
        store.create_profile("my-profile", skills=["translator", "code-reviewer"])
        store.remove_skill_from_profile("my-profile", "translator")
        profile = store.get_profile("my-profile")
        assert "translator" not in profile["skills"]
        assert "code-reviewer" in profile["skills"]

    def test_remove_skill_from_profile_nonexistent(self, store):
        """测试从不存在的 Profile 移除 Skill。"""
        with pytest.raises(StoreError, match="not found"):
            store.remove_skill_from_profile("nonexistent", "translator")


class TestIndexRecovery:
    """索引损坏恢复测试。"""

    def test_corrupted_index_recovers(self, store, sample_skill_dir):
        """索引文件 JSON 损坏时自动使用空索引。"""
        store.install(sample_skill_dir)
        # 破坏索引文件
        store.index_path.write_text("这不是合法的 JSON", encoding="utf-8")
        store._index_cache = None  # 清除缓存迫使其重读
        # 不应该崩溃，应该返回空列表
        skills = store.list_all()
        assert isinstance(skills, list)

    def test_corrupted_index_with_backup(self, store, sample_skill_dir):
        """主索引损坏但有有效备份时，从备份恢复。"""
        store.install(sample_skill_dir)
        # 备份已由 _save_index 自动创建
        # 破坏主索引
        store.index_path.write_text("损坏的内容", encoding="utf-8")
        store._index_cache = None
        skills = store.list_all()
        # 应该从备份恢复
        assert len(skills) > 0

    def test_both_corrupted_index_and_backup(self, store, sample_skill_dir):
        """主索引和备份都损坏时，返回空列表。"""
        store.install(sample_skill_dir)
        # 破坏主索引和备份
        store.index_path.write_text("损坏", encoding="utf-8")
        backup = store.index_path.with_suffix(".json.bak")
        backup.write_text("也损坏", encoding="utf-8")
        store._index_cache = None
        skills = store.list_all()
        assert skills == []

    def test_missing_directory_auto_cleanup(self, store, sample_skill_dir):
        """手动删除 skill 目录后，list_all 自动清理索引。"""
        result = store.install(sample_skill_dir)
        name = result.name  # 使用安装后返回的实际名称（来自 frontmatter）
        assert name == "test-skill"
        import shutil
        shutil.rmtree(store.store_dir / name)
        skills = store.list_all()
        assert all(s.name != name for s in skills)

    def test_backup_created_on_save(self, store, sample_skill_dir):
        """保存索引时自动创建备份文件。"""
        store.install(sample_skill_dir)
        backup = store.index_path.with_suffix(".json.bak")
        assert backup.exists()
        data = json.loads(backup.read_text(encoding="utf-8"))
        assert "skills" in data
