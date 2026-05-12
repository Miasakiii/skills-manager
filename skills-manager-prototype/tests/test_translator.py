"""测试翻译模块。"""

import json
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest

from skills_manager.translator import (
    _detect_language,
    _translate_mymemory,
    _translate_google,
    _translate_lingva,
    translate_text,
    translate_skill_md,
)


# ── _detect_language ─────────────────────────────────────────


class TestDetectLanguage:
    def test_empty_string(self):
        assert _detect_language("") == "en"

    def test_pure_english(self):
        assert _detect_language("Hello world") == "en"

    def test_pure_chinese(self):
        assert _detect_language("你好世界") == "zh"

    def test_chinese_boundary(self):
        """CJK > 30% → zh（先于 en 检查）。"""
        assert _detect_language("abcd你好谢谢") == "zh"

    def test_english_boundary(self):
        """CJK < 30% 且 ASCII > 70% → en。"""
        assert _detect_language("abcde你好") == "en"

    def test_numbers_only(self):
        assert _detect_language("12345") == "en"

    def test_chinese_with_punctuation(self):
        assert _detect_language("你好，世界！") == "zh"

    def test_technical_mixed(self):
        # 技术文档通常英文 > 70%，但含中文
        result = _detect_language("使用 translate API 进行翻译")
        assert result in ("zh", "mixed")


# ── Backend translation (mocked) ────────────────────────────


class TestTranslateMyMemory:
    def test_success(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "responseData": {"translatedText": "你好世界"}
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("skills_manager.translator.urlopen", return_value=mock_response):
            result = _translate_mymemory("Hello world", "zh-CN")
            assert result == "你好世界"

    def test_failure_returns_original(self):
        with patch("skills_manager.translator.urlopen", side_effect=URLError("timeout")):
            result = _translate_mymemory("Hello world", "zh-CN")
            assert result == "Hello world"


class TestTranslateGoogle:
    def test_success(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            [["你好", "Hello", None, None], ["世界", "world", None, None]]
        ]).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("skills_manager.translator.urlopen", return_value=mock_response):
            result = _translate_google("Hello world", "zh-CN")
            assert result == "你好世界"

    def test_failure_returns_original(self):
        with patch("skills_manager.translator.urlopen", side_effect=URLError("timeout")):
            result = _translate_google("Hello world", "zh-CN")
            assert result == "Hello world"


class TestTranslateLingva:
    def test_success(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "translation": "你好世界"
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("skills_manager.translator.urlopen", return_value=mock_response):
            result = _translate_lingva("Hello world", "zh-CN")
            assert result == "你好世界"

    def test_failure_returns_original(self):
        with patch("skills_manager.translator.urlopen", side_effect=URLError("timeout")):
            result = _translate_lingva("Hello world", "zh-CN")
            assert result == "Hello world"


# ── translate_text (fallback chain) ─────────────────────────


class TestTranslateText:
    def test_empty_returns_original(self):
        assert translate_text("") == ""

    def test_none_returns_none(self):
        assert translate_text(None) is None

    def test_fallback_chain(self):
        """第一个后端失败，第二个成功。"""
        with patch("skills_manager.translator._translate_mymemory", return_value="Hello world"), \
             patch("skills_manager.translator._translate_google", return_value="你好世界"), \
             patch("skills_manager.translator._translate_lingva", return_value="你好世界"):
            result = translate_text("Hello world", "zh-CN")
            # MyMemory 返回原文，会尝试下一个
            assert result == "你好世界"

    def test_all_backends_fail_returns_original(self):
        with patch("skills_manager.translator._translate_mymemory", return_value="Hello world"), \
             patch("skills_manager.translator._translate_google", return_value="Hello world"), \
             patch("skills_manager.translator._translate_lingva", return_value="Hello world"):
            result = translate_text("Hello world", "zh-CN")
            assert result == "Hello world"


# ── translate_skill_md ──────────────────────────────────────


class TestTranslateSkillMd:
    def test_single_line_description(self):
        content = """---
name: hello
version: "1.0.0"
description: "A simple greeting tool"
---

## 功能

向用户打招呼。
"""
        with patch("skills_manager.translator.translate_text", return_value="一个简单问候工具"):
            result = translate_skill_md(content, "zh-CN")
            assert 'description: "一个简单问候工具"' in result

    def test_multiline_summary(self):
        content = """---
name: hello
version: "1.0.0"
description: "A tool"
summary: |
  This is a simple
  greeting tool.
---

## 功能

向用户打招呼。
"""
        with patch("skills_manager.translator.translate_text", return_value="这是一个简单的\n问候工具。"):
            result = translate_skill_md(content, "zh-CN")
            assert "这是一个简单的" in result
            assert "问候工具。" in result

    def test_no_frontmatter_returns_original(self):
        content = "## 功能\n没有 frontmatter"
        result = translate_skill_md(content)
        assert result == content

    def test_bom_handling(self):
        """带 BOM 的 SKILL.md 应正确解析。"""
        content = "﻿---\nname: hello\nversion: \"1.0\"\ndescription: \"A tool\"\n---\nBody"
        with patch("skills_manager.translator.translate_text", return_value="一个工具"):
            result = translate_skill_md(content, "zh-CN")
            # 结果应以 --- 开头（BOM 由 _split_frontmatter 处理）
            assert "---" in result

    def test_preserves_non_description_fields(self):
        """不应翻译非 description/summary 字段。"""
        content = """---
name: hello
version: "1.0.0"
description: "A tool"
tags: [demo, greeting]
---

Body.
"""
        with patch("skills_manager.translator.translate_text", return_value="一个工具"):
            result = translate_skill_md(content, "zh-CN")
            assert "tags: [demo, greeting]" in result

    def test_chinese_to_english(self):
        """中文→英文翻译方向。"""
        content = """---
name: hello
version: "1.0.0"
description: "一个简单工具"
---

Body.
"""
        with patch("skills_manager.translator.translate_text", return_value="A simple tool"):
            result = translate_skill_md(content, "en")
            assert 'description: "A simple tool"' in result

    def test_empty_description_not_translated(self):
        """空 description 经 translate_text 返回原文。"""
        content = """---
name: hello
version: "1.0.0"
description: ""
---

Body.
"""
        with patch("skills_manager.translator.translate_text", return_value="") as mock_translate:
            result = translate_skill_md(content, "zh-CN")
            # translate_text 会被调用但返回空字符串
            mock_translate.assert_called_once()
            # 空 description 保持不变
            assert 'description: ""' in result

    def test_description_with_dashes(self):
        """description 中包含 --- 不应截断。"""
        content = '---\nname: hello\nversion: "1.0"\ndescription: "Use --- for separators"\n---\n\nBody'
        with patch("skills_manager.translator.translate_text", return_value="使用---作为分隔符"):
            result = translate_skill_md(content, "zh-CN")
            assert "作为分隔符" in result
            # 正文应保留
            assert "Body" in result
