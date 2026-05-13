"""测试所有适配器。"""

import json

import pytest

from skills_manager.adapters import (
    ClaudeAdapter,
    GeminiAdapter,
    JsonSchemaAdapter,
    MCPAdapter,
    OpenAIAdapter,
    get_adapter,
    list_formats,
)
from skills_manager.ir import Parameter, SkillIR
from skills_manager.parser import parse_skill_content


@pytest.fixture
def sample_ir() -> SkillIR:
    """创建一个标准测试 IR。"""
    content = """---
name: translator
version: "1.0.0"
description: 多语言翻译，支持 7 种语言
summary: 翻译工具
type: tool
tags: [translation]
---

## 功能

翻译文本。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| text | string | ✅ | 待翻译文本 |
| target_lang | string | ✅ | 目标语言：zh / en / ja / ko |
| style | string | ❌ | 风格：formal / casual |

## 示例

```json
{"text": "Hello", "target_lang": "zh"}
```

```json
{"translated_text": "你好"}
```
"""
    return parse_skill_content(content)


@pytest.fixture
def minimal_ir() -> SkillIR:
    """无参数的最小 IR。"""
    return SkillIR(
        name="hello",
        version="1.0.0",
        description="Say hello",
    )


class TestOpenAIAdapter:
    def test_basic_export(self, sample_ir):
        adapter = OpenAIAdapter()
        result = json.loads(adapter.export(sample_ir))

        assert result["type"] == "function"
        assert result["function"]["name"] == "translator"
        assert result["function"]["description"] == "多语言翻译，支持 7 种语言"
        assert result["function"]["strict"] is True

        params = result["function"]["parameters"]
        assert params["type"] == "object"
        assert "text" in params["properties"]
        assert "target_lang" in params["properties"]
        assert "style" in params["properties"]
        assert params["required"] == ["text", "target_lang"]

        # 检查枚举值
        assert params["properties"]["target_lang"]["enum"] == ["zh", "en", "ja", "ko"]
        assert params["properties"]["style"]["enum"] == ["formal", "casual"]

    def test_no_params(self, minimal_ir):
        adapter = OpenAIAdapter()
        result = json.loads(adapter.export(minimal_ir))
        assert result["function"]["name"] == "hello"
        assert "required" not in result["function"]["parameters"]

    def test_file_extension(self):
        assert OpenAIAdapter().file_extension == ".json"


class TestClaudeAdapter:
    def test_basic_export(self, sample_ir):
        adapter = ClaudeAdapter()
        result = json.loads(adapter.export(sample_ir))

        assert "name" in result
        assert "description" in result
        assert "input_schema" in result
        assert result["name"] == "translator"
        assert "text" in result["input_schema"]["properties"]

    def test_no_type_wrapper(self, sample_ir):
        """Claude 格式没有外层 type:function 包裹。"""
        adapter = ClaudeAdapter()
        result = json.loads(adapter.export(sample_ir))
        assert "type" not in result  # 没有外层 type
        assert "input_schema" in result  # 用 input_schema 而非 parameters


class TestGeminiAdapter:
    def test_basic_export(self, sample_ir):
        adapter = GeminiAdapter()
        result = json.loads(adapter.export(sample_ir))

        assert "function_declarations" in result
        decl = result["function_declarations"][0]
        assert decl["name"] == "translator"
        assert decl["description"] == "多语言翻译，支持 7 种语言"

        params = decl["parameters"]
        assert params["type"] == "OBJECT"  # Gemini 用大写
        assert params["properties"]["text"]["type"] == "STRING"

    def test_type_mapping(self, sample_ir):
        adapter = GeminiAdapter()
        result = json.loads(adapter.export(sample_ir))
        props = result["function_declarations"][0]["parameters"]["properties"]
        assert props["text"]["type"] == "STRING"

    def test_nested_and_default(self):
        """验证嵌套类型和 default 字段正确转换为大写类型名。"""
        from skills_manager.ir import SkillIR

        ir = SkillIR(
            name="test",
            version="1.0.0",
            description="test",
            parameters=[
                Parameter(
                    name="items",
                    type="array",
                    description="list",
                    required=False,
                    default=[],
                ),
                Parameter(
                    name="config", type="object", description="obj", required=False
                ),
            ],
        )
        adapter = GeminiAdapter()
        result = json.loads(adapter.export(ir))
        params = result["function_declarations"][0]["parameters"]
        assert params["type"] == "OBJECT"
        assert params["properties"]["items"]["type"] == "ARRAY"
        assert params["properties"]["config"]["type"] == "OBJECT"
        assert params["properties"]["items"].get("default") == []
        assert params.get("additionalProperties") is False


class TestMCPAdapter:
    def test_generates_python(self, sample_ir):
        adapter = MCPAdapter()
        result = adapter.export(sample_ir)

        assert result.startswith("#!/usr/bin/env python3")
        assert "Server('translator')" in result
        assert "inputSchema" in result
        assert "from mcp.server" in result
        assert "asyncio.run(main())" in result

    def test_custom_function_name(self):
        ir = SkillIR(
            name="test",
            version="1.0.0",
            description="Test",
            executor={"type": "python", "entry": "handler.py", "function": "do_test"},
        )
        # 由于 executor 是 dict 而非 ExecutorConfig，需要调整
        from skills_manager.ir import ExecutorConfig

        ir.executor = ExecutorConfig(
            type="python", entry="handler.py", function="do_test"
        )
        adapter = MCPAdapter()
        result = adapter.export(ir)
        assert "from handler import do_test" in result


class TestJsonSchemaAdapter:
    def test_basic_export(self, sample_ir):
        adapter = JsonSchemaAdapter()
        result = json.loads(adapter.export(sample_ir))

        assert result["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert result["title"] == "translator"
        assert result["type"] == "object"
        assert "text" in result["properties"]


class TestAdapterRegistry:
    def test_list_formats(self):
        formats = list_formats()
        assert "openai" in formats
        assert "claude" in formats
        assert "gemini" in formats
        assert "mcp" in formats
        assert "schema" in formats

    def test_get_adapter(self):
        adapter = get_adapter("openai")
        assert isinstance(adapter, OpenAIAdapter)

    def test_unknown_format(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            get_adapter("unknown")


class TestBatchExport:
    def test_batch_openai(self, sample_ir, minimal_ir):
        adapter = OpenAIAdapter()
        result = json.loads(adapter.export_batch([sample_ir, minimal_ir]))
        assert len(result) == 2
        assert result[0]["function"]["name"] == "translator"
        assert result[1]["function"]["name"] == "hello"
