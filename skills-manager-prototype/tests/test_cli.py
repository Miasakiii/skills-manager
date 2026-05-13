"""测试 CLI 命令行接口。"""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from skills_manager.cli import app
from skills_manager.store import Store

runner = CliRunner()


@pytest.fixture
def store(tmp_path, monkeypatch) -> Store:
    """创建临时 Store 实例并 monkeypatch CLI 使用。"""
    store = Store(base_dir=tmp_path / ".skills")
    monkeypatch.setattr("skills_manager.cli.Store", lambda: store)
    return store


@pytest.fixture
def sample_skill_dir(tmp_path) -> Path:
    """创建示例 Skill 目录。"""
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
    (skill_dir / "handler.py").write_text(
        "def run(input): return input", encoding="utf-8"
    )
    return skill_dir


class TestCLIBasic:
    """基本 CLI 命令测试。"""

    def test_help(self):
        """测试帮助命令。"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AI Skill" in result.output

    def test_version(self):
        """测试版本命令。"""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "skills-manager" in result.output


class TestCLIInstall:
    """安装命令测试。"""

    def test_install_from_dir(self, store, sample_skill_dir):
        """测试从目录安装。"""
        result = runner.invoke(app, ["install", str(sample_skill_dir)])
        assert result.exit_code == 0
        assert "Installed" in result.output
        assert store.exists("test-skill")

    def test_install_with_custom_name(self, store, sample_skill_dir):
        """测试自定义名称安装。"""
        result = runner.invoke(
            app, ["install", str(sample_skill_dir), "--name", "custom"]
        )
        assert result.exit_code == 0
        assert store.exists("custom")

    def test_install_force(self, store, sample_skill_dir):
        """测试强制安装。"""
        runner.invoke(app, ["install", str(sample_skill_dir)])
        result = runner.invoke(app, ["install", str(sample_skill_dir), "--force"])
        assert result.exit_code == 0

    def test_install_nonexistent(self, store, tmp_path):
        """测试安装不存在的目录。"""
        result = runner.invoke(app, ["install", str(tmp_path / "nonexistent")])
        assert result.exit_code == 1

    def test_install_from_package(self, store, sample_skill_dir, tmp_path):
        """测试从 .skill 包安装。"""
        from skills_manager.packager import pack

        # 先打包
        packed = pack(sample_skill_dir, tmp_path)

        # 从包安装
        result = runner.invoke(app, ["install", str(packed)])
        assert result.exit_code == 0
        assert store.exists("test-skill")


class TestCLIUninstall:
    """卸载命令测试。"""

    def test_uninstall(self, store, sample_skill_dir):
        """测试卸载。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["uninstall", "test-skill"])
        assert result.exit_code == 0
        assert "Uninstalled" in result.output
        assert not store.exists("test-skill")

    def test_uninstall_nonexistent(self, store):
        """测试卸载不存在的 skill（静默成功）。"""
        result = runner.invoke(app, ["uninstall", "nonexistent"])
        # Store.uninstall 对不存在的 skill 不会报错
        assert result.exit_code == 0


class TestCLIList:
    """列表命令测试。"""

    def test_list_empty(self, store):
        """测试空列表。"""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No installed skills" in result.output

    def test_list_with_skills(self, store, sample_skill_dir):
        """测试有 skill 时的列表。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_list_verbose(self, store, sample_skill_dir):
        """测试详细列表。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["list", "--verbose"])
        assert result.exit_code == 0
        assert "test-skill" in result.output


class TestCLIInfo:
    """详情命令测试。"""

    def test_info(self, store, sample_skill_dir):
        """测试查看详情。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["info", "test-skill"])
        assert result.exit_code == 0
        assert "test-skill" in result.output
        assert "1.0.0" in result.output

    def test_info_nonexistent(self, store):
        """测试查看不存在的 skill。"""
        result = runner.invoke(app, ["info", "nonexistent"])
        assert result.exit_code == 1


class TestCLISearch:
    """搜索命令测试。"""

    def test_search(self, store, sample_skill_dir):
        """测试搜索。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["search", "test"])
        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_search_no_results(self, store, sample_skill_dir):
        """测试搜索无结果。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["search", "nonexistent"])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_search_by_category(self, store, sample_skill_dir):
        """测试按分类搜索。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["search", "test", "--category", "misc"])
        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_search_by_tag(self, store, sample_skill_dir):
        """测试按标签搜索。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["search", "test", "--tag", "test"])
        assert result.exit_code == 0
        assert "test-skill" in result.output


class TestCLIExport:
    """导出命令测试。"""

    def test_export_single(self, store, sample_skill_dir):
        """测试导出单个 skill。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["export", "test-skill", "--format", "openai"])
        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_export_to_file(self, store, sample_skill_dir, tmp_path):
        """测试导出到文件。"""
        store.install(sample_skill_dir)
        output = tmp_path / "output.json"
        result = runner.invoke(
            app,
            [
                "export",
                "test-skill",
                "--format",
                "openai",
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_export_all(self, store, sample_skill_dir):
        """测试导出所有。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["export", "--all", "--format", "openai"])
        assert result.exit_code == 0

    def test_export_nonexistent(self, store):
        """测试导出不存在的 skill。"""
        result = runner.invoke(app, ["export", "nonexistent"])
        assert result.exit_code == 1

    def test_export_invalid_format(self, store, sample_skill_dir):
        """测试无效格式。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["export", "test-skill", "--format", "invalid"])
        assert result.exit_code == 1

    def test_export_current_dir(self, store, sample_skill_dir, monkeypatch):
        """测试从当前目录导出。"""
        monkeypatch.chdir(sample_skill_dir)
        result = runner.invoke(app, ["export", "--current-dir"])
        assert result.exit_code == 0

    def test_export_current_dir_no_skill_md(self, store, tmp_path, monkeypatch):
        """测试当前目录无 SKILL.md。"""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["export", "--current-dir"])
        assert result.exit_code == 1


class TestCLIPack:
    """打包命令测试。"""

    def test_pack(self, store, sample_skill_dir, tmp_path):
        """测试打包。"""
        output = tmp_path / "output"
        result = runner.invoke(
            app, ["pack", str(sample_skill_dir), "--output", str(output)]
        )
        assert result.exit_code == 0
        assert "Packed" in result.output

    def test_pack_nonexistent(self, store, tmp_path):
        """测试打包不存在的目录。"""
        result = runner.invoke(app, ["pack", str(tmp_path / "nonexistent")])
        assert result.exit_code == 1


class TestCLIDoctor:
    """环境检查命令测试。"""

    def test_doctor(self, store):
        """测试环境检查。"""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "Skills Manager Doctor" in result.output
        assert "Version" in result.output


class TestCLIUpgrade:
    """升级命令测试。"""

    def test_upgrade(self, store, sample_skill_dir, tmp_path):
        """测试升级。"""
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
        (new_version_dir / "handler.py").write_text(
            "def run(input): return input", encoding="utf-8"
        )

        result = runner.invoke(app, ["upgrade", "test-skill", str(new_version_dir)])
        assert result.exit_code == 0
        assert "Upgraded" in result.output

    def test_upgrade_nonexistent(self, store, tmp_path):
        """测试升级不存在的 skill。"""
        new_version_dir = tmp_path / "new-version"
        new_version_dir.mkdir()
        (new_version_dir / "SKILL.md").write_text(
            "---\nname: test\nversion: 1.0.0\ndescription: Test\n---\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["upgrade", "nonexistent", str(new_version_dir)])
        assert result.exit_code == 1


class TestCLIRollback:
    """回滚命令测试。"""

    def test_rollback(self, store, sample_skill_dir, tmp_path):
        """测试回滚。"""
        # 安装 v1
        store.install(sample_skill_dir)

        # 升级到 v2
        new_version_dir = tmp_path / "v2"
        new_version_dir.mkdir()
        (new_version_dir / "SKILL.md").write_text(
            "---\nname: test-skill\nversion: 2.0.0\ndescription: V2\n---\n",
            encoding="utf-8",
        )
        store.upgrade("test-skill", new_version_dir)

        # 回滚
        result = runner.invoke(app, ["rollback", "test-skill"])
        assert result.exit_code == 0
        assert "Rolled back" in result.output

    def test_rollback_nonexistent(self, store):
        """测试回滚不存在的 skill。"""
        result = runner.invoke(app, ["rollback", "nonexistent"])
        assert result.exit_code == 1


class TestCLIHistory:
    """版本历史命令测试。"""

    def test_history(self, store, sample_skill_dir):
        """测试查看版本历史。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["history", "test-skill"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_history_nonexistent(self, store):
        """测试查看不存在的 skill 的历史。"""
        result = runner.invoke(app, ["history", "nonexistent"])
        assert result.exit_code == 0
        assert "No version history" in result.output


# ── Translate / Reclassify / Check-Update ────────────────────


class CLITranslate:
    """翻译命令测试。"""

    def test_translate_skill(self, store, sample_skill_dir):
        """测试翻译单个 skill。"""
        store.install(sample_skill_dir)
        with patch("skills_manager.cli.translate_skill_md", return_value="已翻译"):
            result = runner.invoke(app, ["translate", "test-skill"])
            assert result.exit_code == 0

    def test_translate_nonexistent(self, store):
        """测试翻译不存在的 skill。"""
        result = runner.invoke(app, ["translate", "nonexistent"])
        assert result.exit_code == 1


class CLIRetranslate:
    """批量翻译命令测试。"""

    def test_translate_all(self, store, sample_skill_dir):
        """测试批量翻译。"""
        store.install(sample_skill_dir)
        with patch("skills_manager.cli.translate_skill_md", return_value="已翻译"):
            result = runner.invoke(app, ["translate-all"])
            assert result.exit_code == 0


class CLIReclassify:
    """重新分类命令测试。"""

    def test_reclassify(self, store, sample_skill_dir):
        """测试重新分类。"""
        store.install(sample_skill_dir)
        result = runner.invoke(app, ["reclassify"])
        assert result.exit_code == 0


class CLICheckUpdate:
    """更新检查命令测试。"""

    def test_check_update(self, store):
        """测试检查更新。"""
        with patch("skills_manager.cli.check_update") as mock_check:
            from skills_manager.updater import UpdateInfo

            mock_check.return_value = UpdateInfo(
                latest_version="9.9.9",
                current_version="0.1.0",
                has_update=True,
                release_url="https://example.com",
                release_notes="New release",
            )
            result = runner.invoke(app, ["check-update"])
            assert result.exit_code == 0
            assert "9.9.9" in result.output
