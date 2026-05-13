"""测试 Skill 格式验证器。"""

from skills_manager.validator import (
    validate_and_parse,
    validate_skill_dir,
    validate_skill_md,
)


class TestValidateSkillMd:
    """测试 SKILL.md 内容验证。"""

    def test_valid_minimal(self):
        content = "---\nname: test\nversion: 1.0.0\ndescription: Test\n---\n"
        result = validate_skill_md(content)
        assert result.valid is True
        assert result.errors == []

    def test_valid_full(self):
        content = """---
name: translator
version: "1.0.0"
description: 多语言翻译
skill_type: interactive
intent: 引导用户完成翻译任务
---
## 功能
翻译文本。
"""
        result = validate_skill_md(content)
        assert result.valid is True
        assert result.errors == []

    def test_missing_frontmatter(self):
        content = "No frontmatter here"
        result = validate_skill_md(content)
        assert result.valid is False
        assert "缺少 YAML frontmatter" in result.errors[0]

    def test_unclosed_frontmatter(self):
        content = "---\nname: test\nNo closing"
        result = validate_skill_md(content)
        assert result.valid is False
        assert "frontmatter 未闭合" in result.errors[0]

    def test_invalid_yaml(self):
        content = "---\nname: test\n  invalid: yaml: here\n---\n"
        result = validate_skill_md(content)
        assert result.valid is False
        assert "YAML 解析失败" in result.errors[0]

    def test_missing_name(self):
        content = "---\nversion: 1.0.0\ndescription: Test\n---\n"
        result = validate_skill_md(content)
        assert result.valid is False
        assert "缺少必填字段: name" in result.errors

    def test_missing_description(self):
        content = "---\nname: test\nversion: 1.0.0\n---\n"
        result = validate_skill_md(content)
        assert result.valid is False
        assert "缺少必填字段: description" in result.errors

    def test_name_too_long(self):
        content = f"---\nname: {'a' * 65}\nversion: 1.0.0\ndescription: Test\n---\n"
        result = validate_skill_md(content)
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "name 长度" in result.warnings[0]

    def test_description_too_long(self):
        content = f"---\nname: test\nversion: 1.0.0\ndescription: {'a' * 201}\n---\n"
        result = validate_skill_md(content)
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "description 长度" in result.warnings[0]

    def test_dir_name_mismatch(self):
        content = "---\nname: translator\nversion: 1.0.0\ndescription: Test\n---\n"
        result = validate_skill_md(content, dir_name="my-skill")
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "目录名" in result.warnings[0]

    def test_dir_name_match(self):
        content = "---\nname: translator\nversion: 1.0.0\ndescription: Test\n---\n"
        result = validate_skill_md(content, dir_name="translator")
        assert result.valid is True
        assert result.warnings == []

    def test_invalid_skill_type(self):
        content = "---\nname: test\nversion: 1.0.0\ndescription: Test\nskill_type: invalid\n---\n"
        result = validate_skill_md(content)
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "skill_type" in result.warnings[0]

    def test_valid_skill_type(self):
        for st in ["component", "interactive", "workflow"]:
            content = f"---\nname: test\nversion: 1.0.0\ndescription: Test\nskill_type: {st}\n---\n"
            result = validate_skill_md(content)
            assert result.valid is True
            assert result.warnings == []


class TestValidateSkillDir:
    """测试 skill 目录验证。"""

    def test_valid_dir(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test\nversion: 1.0.0\ndescription: Test\n---\n",
            encoding="utf-8",
        )
        result = validate_skill_dir(skill_dir)
        assert result.valid is True

    def test_nonexistent_dir(self, tmp_path):
        skill_dir = tmp_path / "nonexistent"
        result = validate_skill_dir(skill_dir)
        assert result.valid is False
        assert "目录不存在" in result.errors[0]

    def test_missing_skill_md(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        result = validate_skill_dir(skill_dir)
        assert result.valid is False
        assert "缺少 SKILL.md" in result.errors[0]

    def test_invalid_skill_md(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("No frontmatter", encoding="utf-8")
        result = validate_skill_dir(skill_dir)
        assert result.valid is False

    def test_dir_name_warning(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: translator\nversion: 1.0.0\ndescription: Test\n---\n",
            encoding="utf-8",
        )
        result = validate_skill_dir(skill_dir)
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "目录名" in result.warnings[0]


class TestValidateAndParse:
    """测试验证并解析。"""

    def test_valid_content(self):
        content = "---\nname: test\nversion: 1.0.0\ndescription: Test\n---\n"
        result, ir = validate_and_parse(content)
        assert result.valid is True
        assert ir is not None
        assert ir.name == "test"

    def test_invalid_content(self):
        content = "No frontmatter"
        result, ir = validate_and_parse(content)
        assert result.valid is False
        assert ir is None

    def test_with_skill_type(self):
        content = """---
name: test
version: 1.0.0
description: Test
skill_type: interactive
intent: 测试意图
---
## 功能
测试。
"""
        result, ir = validate_and_parse(content)
        assert result.valid is True
        assert ir is not None
        assert ir.skill_type == "interactive"
        assert ir.intent == "测试意图"
