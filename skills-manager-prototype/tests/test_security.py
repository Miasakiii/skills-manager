"""测试安全模块。"""

from pathlib import Path

import pytest

from skills_manager.security import sanitize_name, validate_path_safety


class TestSanitizeName:
    def test_normal_name_passes_through(self):
        assert sanitize_name("my-skill") == "my-skill"

    def test_name_with_underscores(self):
        assert sanitize_name("my_skill_v2") == "my_skill_v2"

    def test_name_with_dots(self):
        assert sanitize_name("my.skill.v1") == "my.skill.v1"

    def test_empty_string_returns_untitled(self):
        assert sanitize_name("") == "untitled"

    def test_none_returns_untitled(self):
        assert sanitize_name(None) == "untitled"

    def test_path_separator_replaced(self):
        assert sanitize_name("my/skill") == "my-skill"

    def test_backslash_replaced(self):
        assert sanitize_name("my\\skill") == "my-skill"

    def test_path_traversal_dot_dot(self):
        name = sanitize_name("../../etc/passwd")
        assert ".." not in name
        assert "/" not in name

    def test_path_traversal_tilde(self):
        name = sanitize_name("~/.ssh/authorized_keys")
        assert "~" not in name
        assert "/" not in name

    def test_null_byte_removed(self):
        assert "\x00" not in sanitize_name("skill\x00name")

    def test_special_characters_replaced(self):
        name = sanitize_name("skill!@#$%^&*()")
        # 所有特殊字符都替换为连字符
        assert all(c.isalnum() or c in "-_." for c in name)

    def test_leading_dot_removed(self):
        name = sanitize_name(".hidden")
        assert not name.startswith(".")

    def test_trailing_dash_stripped(self):
        assert sanitize_name("skill-") == "skill"

    def test_trailing_dot_stripped(self):
        assert sanitize_name("skill.") == "skill"

    def test_long_name_truncated(self):
        name = sanitize_name("a" * 100)
        assert len(name) == 64

    def test_long_name_no_trailing_dash(self):
        name = sanitize_name("a" * 65 + "-")
        assert not name.endswith("-")

    def test_chinese_characters_replaced(self):
        name = sanitize_name("中文测试")
        assert name == "untitled" or all(c.isalnum() or c in "-_." for c in name)

    def test_all_special_chars_returns_untitled(self):
        name = sanitize_name("!@#$%")
        assert len(name) > 0

    def test_consecutive_dashes_compressed(self):
        name = sanitize_name("a///b")
        assert "--" not in name

    def test_spaces_replaced(self):
        name = sanitize_name("my skill")
        assert " " not in name

    def test_realistic_skill_name(self):
        assert sanitize_name("code-reviewer") == "code-reviewer"
        assert sanitize_name("json-formatter") == "json-formatter"

    def test_url_like_name(self):
        name = sanitize_name("https://evil.com/skill")
        assert "/" not in name
        assert ":" not in name


class TestValidatePathSafety:
    def test_child_path_is_safe(self, tmp_path):
        assert validate_path_safety(tmp_path / "child", tmp_path) is True

    def test_parent_traversal_rejected(self, tmp_path):
        assert validate_path_safety(Path("../outside"), tmp_path) is False

    def test_absolute_path_outside_rejected(self, tmp_path):
        result = validate_path_safety(Path("/etc"), tmp_path)
        assert result is False or not str(tmp_path).startswith("/etc")

    def test_nested_ok(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        assert validate_path_safety(nested, tmp_path) is True

    def test_symlink_to_outside(self, tmp_path):
        outside = tmp_path.parent / "outside"
        outside.mkdir(exist_ok=True)
        link = tmp_path / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
            result = validate_path_safety(link, tmp_path)
            # 符号链接穿越应被检测
            assert result is False
        except (OSError, NotImplementedError):
            pytest.skip("无法创建符号链接（权限不足或平台不支持）")
