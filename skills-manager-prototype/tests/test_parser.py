"""测试 SKILL.md 解析器。"""

import json
from pathlib import Path

import pytest

from skills_manager.ir import SkillIR
from skills_manager.parser import (
    ParseError,
    _detect_enum,
    _extract_examples,
    _extract_list,
    _extract_section,
    _extract_table,
    _split_frontmatter,
    parameters_to_json_schema,
    parse_skill_content,
    parse_skill_md,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_SKILL = FIXTURES / "sample-skill" / "SKILL.md"


class TestSplitFrontmatter:
    def test_valid_frontmatter(self):
        content = "---\nname: test\nversion: 1.0.0\n---\nBody here"
        fm, body = _split_frontmatter(content)
        assert "name: test" in fm
        assert "Body here" in body

    def test_no_frontmatter(self):
        content = "No frontmatter here"
        fm, body = _split_frontmatter(content)
        assert fm == ""
        assert body == content

    def test_bom_handling(self):
        content = "\ufeff---\nname: test\n---\nBody"
        fm, body = _split_frontmatter(content)
        assert "name: test" in fm

    def test_incomplete_frontmatter(self):
        content = "---\nname: test\nNo closing"
        fm, body = _split_frontmatter(content)
        assert fm == ""
        assert body == content


class TestExtractSection:
    def test_extract_existing_section(self):
        body = "## 功能\nSome content\n## 参数\n| a | b |"
        result = _extract_section(body, "功能")
        assert result == "Some content"

    def test_missing_section(self):
        body = "## 功能\nContent"
        result = _extract_section(body, "参数")
        assert result == ""

    def test_section_with_multiple_paragraphs(self):
        body = "## 功能\nParagraph 1\n\nParagraph 2\n\n## 参数"
        result = _extract_section(body, "功能")
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result


class TestExtractTable:
    def test_valid_table(self):
        body = """## 参数
| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| text | string | ✅ | 输入文本 |
| lang | string | ❌ | 目标语言 |
"""
        rows = _extract_table(body, "参数")
        assert len(rows) == 2
        assert rows[0]["参数"] == "text"
        assert rows[0]["类型"] == "string"
        assert rows[0]["必需"] == "✅"
        assert rows[1]["必需"] == "❌"

    def test_no_table(self):
        body = "## 参数\nNo table here"
        rows = _extract_table(body, "参数")
        assert rows == []

    def test_empty_table(self):
        body = "## 参数\n| a | b |\n|---|---|\n"
        rows = _extract_table(body, "参数")
        assert rows == []


class TestDetectEnum:
    def test_slash_format(self):
        assert _detect_enum("语言：zh / en / ja") == ["zh", "en", "ja"]

    def test_comma_format(self):
        assert _detect_enum("风格：formal,casual,technical") == [
            "formal",
            "casual",
            "technical",
        ]

    def test_no_enum(self):
        assert _detect_enum("普通描述文本") is None

    def test_colon_prefix(self):
        assert _detect_enum("Type: a / b / c") == ["a", "b", "c"]


class TestExtractExamples:
    def test_json_blocks(self):
        body = """## 示例
输入：
```json
{"text": "hello"}
```
输出：
```json
{"result": "world"}
```
"""
        examples = _extract_examples(body)
        assert len(examples) == 1
        assert examples[0].input == {"text": "hello"}
        assert examples[0].output == {"result": "world"}

    def test_no_examples(self):
        examples = _extract_examples("## 示例\nNo code blocks")
        assert examples == []


class TestExtractList:
    def test_dash_list(self):
        body = "## 适用场景\n- Item 1\n- Item 2\n"
        items = _extract_list(body, "适用场景")
        assert items == ["Item 1", "Item 2"]

    def test_star_list(self):
        body = "## 不适用\n* Item A\n* Item B\n"
        items = _extract_list(body, "不适用")
        assert items == ["Item A", "Item B"]

    def test_no_list(self):
        items = _extract_list("## 适用场景\nNo list", "适用场景")
        assert items == []


class TestParseSkillContent:
    def test_minimal_content(self):
        content = "---\nname: hello\nversion: 1.0.0\ndescription: Hi\n---\n"
        ir = parse_skill_content(content)
        assert ir.name == "hello"
        assert ir.version == "1.0.0"
        assert ir.description == "Hi"

    def test_full_content(self):
        content = """---
name: translator
version: "1.0.0"
description: 多语言翻译
summary: 翻译工具
type: tool
tags: [translation, i18n]
category: language
---

## 功能

翻译文本。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| text | string | ✅ | 输入文本 |
| target_lang | string | ✅ | 目标语言：zh / en / ja |
| style | string | ❌ | 风格：formal / casual |

## 示例

```json
{"text": "hello", "target_lang": "zh"}
```

```json
{"translated_text": "你好"}
```

## 适用场景

- 翻译文本

## 不适用

- 实时翻译
"""
        ir = parse_skill_content(content)
        assert ir.name == "translator"
        assert ir.version == "1.0.0"
        assert len(ir.parameters) == 3
        assert ir.parameters[0].name == "text"
        assert ir.parameters[0].required is True
        assert ir.parameters[2].enum == ["formal", "casual"]
        assert ir.tags == ["translation", "i18n"]
        assert ir.category == "language"
        assert len(ir.examples) == 1
        assert ir.use_cases == ["翻译文本"]
        assert ir.not_for == ["实时翻译"]

    def test_name_fallback(self):
        content = "---\nversion: 1.0.0\ndescription: test\n---\n"
        ir = parse_skill_content(content, name_hint="fallback")
        assert ir.name == "fallback"


class TestParseSkillMd:
    def test_parse_sample(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test\nversion: 1.0.0\ndescription: Test\n---\n",
            encoding="utf-8",
        )
        ir = parse_skill_md(skill_dir / "SKILL.md")
        assert ir.name == "test"


class TestParametersToJsonSchema:
    def test_basic_schema(self):
        from skills_manager.ir import Parameter

        params = [
            Parameter(name="text", type="string", description="Input text", required=True),
            Parameter(name="count", type="integer", description="Count"),
        ]
        schema = parameters_to_json_schema(params)
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert schema["required"] == ["text"]
        assert schema["properties"]["text"]["type"] == "string"

    def test_enum_in_schema(self):
        from skills_manager.ir import Parameter

        params = [
            Parameter(
                name="lang",
                type="string",
                description="Language",
                enum=["zh", "en"],
            ),
        ]
        schema = parameters_to_json_schema(params)
        assert schema["properties"]["lang"]["enum"] == ["zh", "en"]
