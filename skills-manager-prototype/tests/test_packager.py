"""测试打包与解包。"""

from pathlib import Path

import pytest

from skills_manager.packager import pack, unpack


@pytest.fixture
def skill_dir(tmp_path) -> Path:
    """创建示例 Skill 目录。"""
    d = tmp_path / "my-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: my-skill\nversion: 1.0.0\ndescription: Test\n---\n",
        encoding="utf-8",
    )
    (d / "handler.py").write_text("print('hello')", encoding="utf-8")
    return d


class TestPack:
    def test_pack_creates_file(self, skill_dir, tmp_path):
        output_dir = tmp_path / "output"
        result = pack(skill_dir, output_dir)
        assert result.exists()
        assert result.suffix == ".skill"
        assert "my-skill" in result.name

    def test_pack_no_skill_md(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(FileNotFoundError, match="No SKILL.md"):
            pack(empty)


class TestUnpack:
    def test_roundtrip(self, skill_dir, tmp_path):
        output_dir = tmp_path / "packed"
        packed = pack(skill_dir, output_dir)

        unpack_dir = tmp_path / "unpacked"
        unpack_dir.mkdir()
        result = unpack(packed, unpack_dir)
        assert (result / "SKILL.md").exists()
        assert (result / "handler.py").exists()

    def test_unpack_nonexistent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            unpack(tmp_path / "nonexistent.skill")
