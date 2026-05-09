# Skills Manager — 技术设计文档

> **版本**：v3.0  
> **日期**：2026-05-08  
> **前置文档**：[任务书](./task-book.md)  
> **变更说明**：Python 优先架构，Flet 桌面 UI，Rust 移植延后为可选优化

---

## 一、整体架构

### 1.1 架构总览

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        Skills Manager                               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Flet 桌面应用                              │   │
│  │                                                             │   │
│  │  ┌──────────────────────────────┐  ┌────────────────────┐  │   │
│  │  │        UI 层（Flet）          │  │   应用控制器        │  │   │
│  │  │                              │  │   （Python）        │  │   │
│  │  │  Flet Controls + Pages       │  │                    │  │   │
│  │  │                              │  │  ┌──────────────┐  │  │   │
│  │  │  ┌────────┐ ┌────────────┐  │  │  │  核心引擎    │  │  │   │
│  │  │  │ 浏览   │ │  编辑器    │  │  │  │              │  │  │   │
│  │  │  │ 搜索   │ │  预览      │  │  │  │  Parser      │  │  │   │
│  │  │  │ 导出   │ │  设置      │  │  │  │  IR          │  │  │   │
│  │  │  │ Profile│ │            │  │  │  │  Adapters    │  │  │   │
│  │  │  └────────┘ └────────────┘  │  │  │  Store       │  │  │   │
│  │  │                              │  │  │  Packager    │  │  │   │
│  │  └──────────────┬───────────────┘  │  └──────────────┘  │  │   │
│  │                 │                   │         │          │  │   │
│  │                 │  Python 直接调用  │         │          │  │   │
│  │                 └───────────────────┼─────────┘          │  │   │
│  │                                     │                    │  │   │
│  └─────────────────────────────────────┼────────────────────┘  │   │
│                                        │                        │   │
│  ┌─────────────────────────────────────┼────────────────────┐  │   │
│  │              核心引擎（Python 包）                          │  │   │
│  │                                     │                    │  │   │
│  │  skills_manager:                    │                    │  │   │
│  │  ├── parser      （SKILL.md → IR）  │                    │  │   │
│  │  ├── ir           （数据结构）       │                    │  │   │
│  │  ├── adapters    （IR → 各平台格式）│                    │  │   │
│  │  ├── store       （本地存储管理）    │                    │  │   │
│  │  ├── packager    （.skill 打包）    │                    │  │   │
│  │  ├── search      （搜索引擎）       │                    │  │   │
│  │  └── recommend   （场景推荐）       │                    │  │   │
│  └─────────────────────────────────────────────────────────┘  │   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              CLI（可选，共享核心引擎）                      │      │
│  │  skills_manager.cli → click/argparse CLI 入口             │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              Rust 扩展（Phase 3.5，可选）                  │      │
│  │  skills_core_rs: PyO3 扩展模块                           │      │
│  │  ├── fast_parser    （drop-in 解析器替换）                │      │
│  │  └── fast_adapters  （drop-in 适配器替换）                │      │
│  └─────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

1. **引擎与 UI 分离**：`skills_manager` 核心是纯逻辑库，不依赖任何 GUI 框架。桌面端和 CLI 都基于它构建。
2. **Python 优先**：所有核心逻辑用 Python 实现。迭代快、调试方便、团队原生。
3. **单一导入路径**：桌面应用和 CLI 一样 `import skills_manager`，无需 IPC 层。
4. **渐进增强**：先跑通最小可用版本（解析 + 导出），再逐步添加 GUI、编辑器、Profile 等功能。
5. **Rust 作为可选加速器**：如 profiling 显示 Python 是瓶颈，通过 PyO3 做 drop-in 替换。无需重写。

### 1.3 项目结构

```text
skills-manager/
├── pyproject.toml                    # 项目元数据 + 依赖
├── README.md
├── task-book.md
├── tech-design.md
├── src/
│   └── skills_manager/
│       ├── __init__.py
│       ├── cli.py                    # CLI 入口（click/argparse）
│       ├── parser.py                 # SKILL.md → IR
│       ├── ir.py                     # IR 数据模型（Pydantic）
│       ├── schema.py                 # Markdown 表格 → JSON Schema
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── base.py              # 适配器 ABC
│       │   ├── openai.py
│       │   ├── claude.py
│       │   ├── gemini.py
│       │   ├── mcp.py
│       │   └── json_schema.py
│       ├── store.py                  # 本地存储（SQLite + 文件）
│       ├── search.py                 # 搜索引擎
│       ├── recommend.py              # 场景推荐
│       ├── packager.py               # .skill 打包/解包
│       └── profile.py               # Profile 管理
├── desktop/
│   ├── main.py                       # Flet 应用入口
│   ├── app.py                        # 应用控制器 / 路由
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── browse.py                 # Skill 浏览页
│   │   ├── detail.py                 # Skill 详情页
│   │   ├── editor.py                 # Skill 编辑器页
│   │   ├── export.py                 # 导出页
│   │   ├── profiles.py              # Profile 管理页
│   │   └── settings.py              # 设置页
│   ├── components/
│   │   ├── __init__.py
│   │   ├── skill_card.py            # Skill 卡片组件
│   │   ├── export_panel.py          # 导出面板
│   │   ├── search_bar.py            # 搜索栏
│   │   ├── category_filter.py       # 分类侧边栏筛选
│   │   ├── markdown_editor.py       # Markdown 编辑器组件
│   │   ├── preview_panel.py         # IR 预览面板
│   │   └── toast.py                 # Toast 通知
│   ├── theme.py                      # 主题定义（亮色/暗色）
│   └── state.py                      # 应用状态管理
├── examples/                         # 示例 Skills
│   ├── translator/SKILL.md
│   ├── json-formatter/SKILL.md
│   └── code-reviewer/SKILL.md
├── tests/
│   ├── test_parser.py
│   ├── test_adapters.py
│   ├── test_store.py
│   ├── test_packager.py
│   ├── test_search.py
│   └── conftest.py
├── rust/                             # Phase 3.5: Rust 扩展（可选）
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs                    # PyO3 入口
│   │   ├── parser.rs
│   │   └── adapters/
│   └── pyproject.toml                # maturin 构建配置
└── docs/
    └── user-guide.md
```

---

## 二、Skill 格式规范

### 2.1 目录结构

```text
my-skill/
├── SKILL.md            # 必需：元数据 + 文档 + 参数定义
├── handler.py          # 可选：执行逻辑（Python）
├── handler.js          # 可选：执行逻辑（Node.js）
├── handler.sh          # 可选：执行逻辑（Shell）
├── config.example.yaml # 可选：用户配置模板
└── tests/
    └── cases.yaml      # 可选：测试用例
```

**设计决策**：只强制一个 `SKILL.md`，其他全部可选。降低上手门槛是第一优先级。

### 2.2 SKILL.md 格式

SKILL.md = YAML frontmatter + Markdown body。

#### Frontmatter（机器可读）

```yaml
---
name: translator                    # 必需：唯一标识，小写 + 连字符
version: "1.0.0"                    # 必需：语义化版本
description: 多语言翻译，支持 7 种语言  # 必需：一句话描述（< 100 字）
summary: |                          # 必需：2-3 句话摘要，用于列表展示和快速理解
  将文本翻译到 7 种目标语言，自动检测源语言。
  支持 formal / casual / technical 三种翻译风格。
  需要配置翻译 API Key（支持 Google / DeepL / 百度）。
type: tool                          # 可选：prompt | tool | workflow | composite，默认 tool
tags: [translation, i18n]           # 可选：自由标签（二级分类）
category: language                  # 可选：一级分类标识（见分类体系）

# 以下为扩展字段，用到时再加
executor:                           # 可选：执行配置
  type: python                      # python | node | shell | http
  entry: handler.py                 # 入口文件
  function: translate               # 入口函数名
config:                             # 可选：用户配置声明
  api_key:
    type: string
    secret: true
    description: 翻译服务 API Key
    required: true
security:                           # 可选：安全声明
  needs_network: true
  needs_api_key: true
author: someone                     # 可选
license: MIT                        # 可选
---
```

**最小可用 frontmatter**（只需 4 个字段）：

```yaml
---
name: hello
version: "1.0.0"
description: 一个简单的问候 Skill
summary: 向用户打招呼，支持中英文。
---
```

#### Markdown Body（人类可读 + 参数定义）

```markdown
## 功能

将文本翻译到目标语言，自动检测源语言并保持术语一致性。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| text | string | ✅ | 待翻译文本，最大 10000 字符 |
| target_lang | string | ✅ | 目标语言：zh / en / ja / ko / fr / de / es |
| style | string | ❌ | 风格：formal / casual / technical，默认 formal |

## 返回

| 字段 | 类型 | 说明 |
|---|---|---|
| translated_text | string | 翻译结果 |
| confidence | number | 置信度 0-1 |
| detected_lang | string | 检测到的源语言 |

## 示例

**输入**：
{"text": "Hello world", "target_lang": "zh"}

**输出**：
{"translated_text": "你好世界", "confidence": 0.95, "detected_lang": "en"}

## 适用场景

- 翻译用户反馈或评论
- 多语言内容本地化

## 不适用

- 实时口语翻译（延迟较高）
- 文学翻译（缺乏文学润色能力）
```

### 2.3 参数表解析规则

工具自动从 Markdown 中的 `## 参数` 表格解析出 JSON Schema。

**解析逻辑**：

```text
输入表格：
| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| text | string | ✅ | 待翻译文本 |
| target_lang | string | ✅ | 目标语言 |
| style | string | ❌ | 风格 |

解析为：
{
  "type": "object",
  "properties": {
    "text": {"type": "string", "description": "待翻译文本"},
    "target_lang": {"type": "string", "description": "目标语言"},
    "style": {"type": "string", "description": "风格"}
  },
  "required": ["text", "target_lang"]
}
```

**类型映射**：

| Markdown 类型 | JSON Schema 类型 | Python 类型 |
| ------------ | --------------- | ---------- |
| string | string | str |
| int / integer | integer | int |
| float / number | number | float |
| bool / boolean | boolean | bool |
| array | array | list |
| object | object | dict |
| string[] | array (items: string) | list[str] |

**枚举值检测**：如果说明中包含 `X / Y / Z` 或 `X,Y,Z` 格式，自动提取为 `enum`。

**fallback**：如果 SKILL.md 中没有 `## 参数` 表格，但 frontmatter 中有 `executor` 配置，则尝试从 handler 的类型注解中解析。

### 2.4 打包格式

`.skill` 文件 = `.tar.gz`，顶层目录为 Skill 名称：

```text
translator-1.0.0.skill
└── translator/
    ├── SKILL.md
    ├── handler.py
    └── ...
```

---

## 三、中间表示（IR）

IR 是所有适配器的统一输入。从 SKILL.md 解析生成。

### 3.1 Python 数据模型（Pydantic）

```python
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ParamType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class SkillType(str, Enum):
    PROMPT = "prompt"
    TOOL = "tool"
    WORKFLOW = "workflow"
    COMPOSITE = "composite"


class Parameter(BaseModel):
    name: str
    type: ParamType
    description: str
    required: bool = False
    enum_values: Optional[list[str]] = None
    default: Optional[object] = None


class Example(BaseModel):
    input: dict
    output: dict


class ExecutorConfig(BaseModel):
    type: str  # "python" | "node" | "shell" | "http"
    entry: str
    function: Optional[str] = None


class SecurityConfig(BaseModel):
    needs_network: bool = False
    needs_api_key: bool = False


class SkillIR(BaseModel):
    """中间表示 — 所有适配器的统一输入。"""

    # 核心标识
    name: str
    version: str
    description: str
    summary: str
    skill_type: SkillType = SkillType.TOOL

    # 参数定义
    parameters: list[Parameter] = Field(default_factory=list)

    # 文档
    functionality: str = ""
    use_cases: list[str] = Field(default_factory=list)
    not_for: list[str] = Field(default_factory=list)
    examples: list[Example] = Field(default_factory=list)

    # 分类
    tags: list[str] = Field(default_factory=list)
    category: Optional[str] = None

    # 执行配置
    executor: Optional[ExecutorConfig] = None
    security: Optional[SecurityConfig] = None
    config: Optional[dict] = None

    # 元信息
    author: Optional[str] = None
    license: Optional[str] = None
```

### 3.2 SKILL.md → IR 解析流程

```text
SKILL.md 文件
    │
    ├── 读取文件内容
    │
    ├── 分离 frontmatter（--- 之间的 YAML）
    │   └── yaml.safe_load → frontmatter 字典
    │       → name, version, description, summary, type, tags, category,
    │         executor, security, config, author, license
    │
    └── 解析 Markdown body
        ├── "## 功能" / "## Functionality"  → functionality (str)
        ├── "## 参数" / "## Parameters"      → parameters[] (正则提取表格 → Parameter)
        ├── "## 返回" / "## Returns"         → 存储备用（适配器可选使用）
        ├── "## 示例" / "## Example"         → examples[] (JSON 块提取)
        ├── "## 适用场景" / "## Use Cases"    → use_cases[] (列表提取)
        └── "## 不适用" / "## Not For"       → not_for[] (列表提取)
```

---

## 四、分类体系

### 4.1 一级分类（固定，不轻易扩展）

| 分类 | 标识 | 图标 | 说明 |
| ---- | ---- | ---- | ---- |
| 语言处理 | `language` | 📝 | 翻译、语法、改写、摘要、信息提取 |
| 编程开发 | `code` | 🔧 | 代码审查、生成、测试、调试、文档、格式化 |
| 数据分析 | `data` | 📊 | 数据分析、可视化、清洗、转换、统计 |
| 信息检索 | `research` | 🔍 | 搜索、爬取、摘要、事实核查 |
| 内容创作 | `writing` | ✍️ | 博客、邮件、文案、创意写作 |
| 流程自动化 | `automation` | ⚡ | 调度、通知、文件管理、集成 |
| Agent 增强 | `agent` | 🤖 | 记忆、规划、推理、工具编排 |
| 其他 | `misc` | 📦 | 无法归类的 Skills |

### 4.2 二级标签（自由扩展）

二级标签写在 SKILL.md 的 `tags` 字段中，不限制，自由命名。

---

## 五、适配器设计

### 5.1 适配器 ABC

```python
from abc import ABC, abstractmethod
from skills_manager.ir import SkillIR


class AdapterError(Exception):
    """适配器基础异常。"""
    pass


class BaseAdapter(ABC):
    """所有格式适配器的基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称（如 'openai', 'claude'）。"""
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """输出文件扩展名（如 '.json', '.py'）。"""
        ...

    @abstractmethod
    def export(self, ir: SkillIR) -> str:
        """将 IR 转换为目标格式字符串。"""
        ...

    def export_batch(self, irs: list[SkillIR]) -> str:
        """批量导出。"""
        import json
        results = [json.loads(self.export(ir)) for ir in irs]
        return json.dumps(results, indent=2, ensure_ascii=False)
```

### 5.2 OpenAI 适配器

```python
import json
from skills_manager.ir import SkillIR
from skills_manager.schema import parameters_to_json_schema
from skills_manager.adapters.base import BaseAdapter


class OpenAIAdapter(BaseAdapter):
    @property
    def name(self) -> str:
        return "openai"

    @property
    def file_extension(self) -> str:
        return ".json"

    def export(self, ir: SkillIR) -> str:
        schema = parameters_to_json_schema(ir.parameters)
        result = {
            "type": "function",
            "function": {
                "name": ir.name,
                "description": ir.description,
                "parameters": schema,
                "strict": True,
            },
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
```

**输出示例**：

```json
{
  "type": "function",
  "function": {
    "name": "translator",
    "description": "多语言翻译，支持 7 种语言",
    "parameters": {
      "type": "object",
      "properties": {
        "text": {"type": "string", "description": "待翻译文本"},
        "target_lang": {"type": "string", "description": "目标语言", "enum": ["zh", "en", "ja", "ko", "fr", "de", "es"]},
        "style": {"type": "string", "description": "翻译风格", "enum": ["formal", "casual", "technical"]}
      },
      "required": ["text", "target_lang"]
    },
    "strict": true
  }
}
```

### 5.3 Claude 适配器

```python
import json
from skills_manager.ir import SkillIR
from skills_manager.schema import parameters_to_json_schema
from skills_manager.adapters.base import BaseAdapter


class ClaudeAdapter(BaseAdapter):
    @property
    def name(self) -> str:
        return "claude"

    @property
    def file_extension(self) -> str:
        return ".json"

    def export(self, ir: SkillIR) -> str:
        schema = parameters_to_json_schema(ir.parameters)
        result = {
            "name": ir.name,
            "description": ir.description,
            "input_schema": schema,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
```

**输出示例**：

```json
{
  "name": "translator",
  "description": "多语言翻译，支持 7 种语言",
  "input_schema": {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "待翻译文本"},
      "target_lang": {"type": "string", "description": "目标语言", "enum": ["zh", "en", "ja", "ko", "fr", "de", "es"]},
      "style": {"type": "string", "description": "翻译风格", "enum": ["formal", "casual", "technical"]}
    },
    "required": ["text", "target_lang"]
  }
}
```

### 5.4 Gemini 适配器

Gemini 使用 `function_declarations` 数组包裹，且类型名大写（`STRING` 而非 `string`）。

```python
import json
from skills_manager.ir import SkillIR
from skills_manager.adapters.base import BaseAdapter


class GeminiAdapter(BaseAdapter):
    @property
    def name(self) -> str:
        return "gemini"

    @property
    def file_extension(self) -> str:
        return ".json"

    def export(self, ir: SkillIR) -> str:
        params = self._parameters_to_gemini_schema(ir.parameters)
        result = {
            "function_declarations": [
                {
                    "name": ir.name,
                    "description": ir.description,
                    "parameters": params,
                }
            ]
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _parameters_to_gemini_schema(self, parameters):
        """将参数转换为 Gemini 格式（大写类型名）。"""
        # ... 类型映射: string→STRING, integer→INTEGER, 等
        pass
```

### 5.5 MCP 适配器

MCP 适配器生成一个可直接运行的 Python 脚本：

```python
import json
from skills_manager.ir import SkillIR
from skills_manager.schema import parameters_to_json_schema
from skills_manager.adapters.base import BaseAdapter


class MCPAdapter(BaseAdapter):
    @property
    def name(self) -> str:
        return "mcp"

    @property
    def file_extension(self) -> str:
        return ".py"

    def export(self, ir: SkillIR) -> str:
        schema = json.dumps(parameters_to_json_schema(ir.parameters), indent=2, ensure_ascii=False)
        function_name = "run"
        if ir.executor and ir.executor.function:
            function_name = ir.executor.function

        return f'''#!/usr/bin/env python3
"""MCP Server for {ir.name} - {ir.description}"""
from mcp.server import Server
from mcp.types import Tool
import json

server = Server("{ir.name}")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="{ir.name}",
            description="{ir.description}",
            inputSchema={schema}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    from handler import {function_name}
    return {function_name}(**arguments)

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read, write):
            await server.run(read, write)

    asyncio.run(main())
'''
```

### 5.6 适配器注册

```python
from skills_manager.adapters.base import BaseAdapter
from skills_manager.adapters.openai import OpenAIAdapter
from skills_manager.adapters.claude import ClaudeAdapter
from skills_manager.adapters.gemini import GeminiAdapter
from skills_manager.adapters.mcp import MCPAdapter
from skills_manager.adapters.json_schema import JsonSchemaAdapter

ADAPTERS: dict[str, BaseAdapter] = {
    "openai": OpenAIAdapter(),
    "claude": ClaudeAdapter(),
    "gemini": GeminiAdapter(),
    "mcp": MCPAdapter(),
    "schema": JsonSchemaAdapter(),
}


def get_adapter(format: str) -> BaseAdapter | None:
    return ADAPTERS.get(format)


def list_adapters() -> list[str]:
    return list(ADAPTERS.keys())
```

---

## 六、存储设计

### 6.1 存储结构

```text
~/.skills-manager/                     # 应用数据目录
├── config.toml                        # 全局配置
├── skills.db                          # SQLite 数据库（索引 + 元数据）
├── store/                             # 已安装 Skills（文件存储）
│   ├── translator/
│   │   ├── SKILL.md
│   │   ├── handler.py
│   │   └── ...
│   └── code-reviewer/
│       └── ...
└── profiles/                          # Agent Profile 文件
    ├── my-chatbot.json
    └── data-agent.json
```

### 6.2 SQLite Schema

```sql
-- Skills 索引表
CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL,
    description TEXT NOT NULL,
    summary TEXT,
    skill_type TEXT DEFAULT 'tool',
    category TEXT,
    author TEXT,
    license TEXT,
    source TEXT,                    -- 安装来源
    install_path TEXT NOT NULL,     -- 文件存储路径
    installed_at TEXT NOT NULL,     -- ISO 8601
    updated_at TEXT
);

-- 标签表（多对多）
CREATE TABLE skill_tags (
    skill_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (skill_id, tag),
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- 全文搜索索引
CREATE VIRTUAL TABLE skills_fts USING fts5(
    name, description, summary, tags,
    content='skills',
    content_rowid='id'
);

-- 导出历史
CREATE TABLE export_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    format TEXT NOT NULL,
    output_path TEXT,
    exported_at TEXT NOT NULL
);

-- 触发器：同步 FTS
CREATE TRIGGER skills_ai AFTER INSERT ON skills BEGIN
    INSERT INTO skills_fts(rowid, name, description, summary)
    VALUES (new.id, new.name, new.description, new.summary);
END;

CREATE TRIGGER skills_ad AFTER DELETE ON skills BEGIN
    INSERT INTO skills_fts(skills_fts, rowid, name, description, summary)
    VALUES ('delete', old.id, old.name, old.description, old.summary);
END;

CREATE TRIGGER skills_au AFTER UPDATE ON skills BEGIN
    INSERT INTO skills_fts(skills_fts, rowid, name, description, summary)
    VALUES ('delete', old.id, old.name, old.description, old.summary);
    INSERT INTO skills_fts(rowid, name, description, summary)
    VALUES (new.id, new.name, new.description, new.summary);
END;
```

### 6.3 全局配置

`~/.skills-manager/config.toml`：

```toml
[general]
default_format = "openai"
language = "zh"
theme = "system"                    # "light" | "dark" | "system"

[store]
path = "~/.skills-manager/store"    # Skill 存储路径

[enrichment]
enabled = false
provider = "openai"                 # "openai" | "claude" | "local"
model = "gpt-4o-mini"
api_key = ""
base_url = "https://api.openai.com/v1"
```

---

## 七、桌面应用设计（Flet）

### 7.1 技术栈

| 组件 | 选择 | 说明 |
| ---- | ---- | ---- |
| UI 框架 | Flet 0.25+ | 基于 Flutter 渲染，Python 原生 |
| 状态管理 | Flet 内置（Page + controls） | 通过 control 属性响应式更新 |
| Markdown 编辑器 | Flet TextField + Markdown widget | 或通过 Flet WebView 嵌入 CodeMirror |
| 代码高亮 | Flet Code widget / 自定义 | 用于导出结果展示 |
| 图标 | Flet Icons（Material） | 统一 Material Design |
| 路由 | Flet implicit routes / 自定义路由 | 客户端页面导航 |
| 主题 | Flet Theme + 自定义 tokens | 亮/暗通过 Flet 主题系统切换 |

### 7.2 页面结构

```text
┌─────────────────────────────────────────────────────────────┐
│  ┌──────────┐  ┌──────────────────────────────────────────┐ │
│  │          │  │                                          │ │
│  │  侧边栏   │  │              内容区                      │ │
│  │          │  │                                          │ │
│  │ 📋 Skills │  │  ┌──────────────────────────────────┐  │ │
│  │   浏览    │  │  │        Skill 卡片网格             │  │ │
│  │   搜索    │  │  │                                  │  │ │
│  │   分类    │  │  │  ┌──────┐ ┌──────┐ ┌──────┐    │  │ │
│  │          │  │  │  │Card 1│ │Card 2│ │Card 3│    │  │ │
│  │ 📤 导出   │  │  │  │      │ │      │ │      │    │  │ │
│  │   单个    │  │  │  └──────┘ └──────┘ └──────┘    │  │ │
│  │   批量    │  │  │  ┌──────┐ ┌──────┐ ┌──────┐    │  │ │
│  │          │  │  │  │Card 4│ │Card 5│ │Card 6│    │  │ │
│  │ 📁 Profile│  │  │  │      │ │      │ │      │    │  │ │
│  │   管理    │  │  │  └──────┘ └──────┘ └──────┘    │  │ │
│  │   导出    │  │  └──────────────────────────────────┘  │ │
│  │          │  │                                          │ │
│  │ 📝 编辑器 │  │  ┌──────────────────────────────────┐  │ │
│  │   新建    │  │  │        Skill 详情面板             │  │ │
│  │   编辑    │  │  │                                  │  │ │
│  │          │  │  │  参数表 | 示例 | 文档 | 导出预览   │  │ │
│  │ ⚙️ 设置   │  │  │                                  │  │ │
│  │          │  │  └──────────────────────────────────┘  │ │
│  └──────────┘  └──────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 核心组件

| 组件 | 说明 |
| ---- | ---- |
| `SkillCard` | Skill 卡片：名称、版本、分类图标、摘要、标签 |
| `SkillDetail` | 详情面板：Tab 切换（参数/示例/文档/导出） |
| `ExportPanel` | 导出面板：格式选择、预览、复制/保存 |
| `SkillEditor` | Markdown 编辑器 + 实时 IR 预览 |
| `CategoryFilter` | 分类筛选侧边栏 |
| `SearchBar` | 实时搜索框 |
| `ProfileManager` | Profile 列表 + 拖拽配置 |
| `BatchExportDialog` | 批量导出对话框 |
| `InstallDialog` | 安装 Skill 对话框（本地路径 / URL） |
| `SettingsPage` | 设置页（主题、默认格式、存储路径） |

### 7.4 应用状态

```python
# desktop/state.py
from dataclasses import dataclass, field
from skills_manager.ir import SkillIR


@dataclass
class AppState:
    """应用状态 — 单一数据源。"""

    # Skill 列表
    skills: list[dict] = field(default_factory=list)  # SkillSummary 字典
    selected_skill: SkillIR | None = None
    search_query: str = ""
    selected_category: str | None = None
    is_loading: bool = False

    # UI 状态
    current_page: str = "browse"
    theme: str = "system"  # "light" | "dark" | "system"

    # 导出状态
    last_export_format: str = "openai"
    export_history: list[dict] = field(default_factory=list)

    def refresh_skills(self, store):
        """从 store 重新加载 skills。"""
        self.is_loading = True
        self.skills = store.list_skills(
            search=self.search_query or None,
            category=self.selected_category or None,
        )
        self.is_loading = False
```

### 7.5 主应用入口

```python
# desktop/main.py
import flet as ft
from skills_manager.store import SkillStore
from desktop.state import AppState
from desktop.pages.browse import BrowsePage
from desktop.pages.detail import DetailPage
from desktop.pages.editor import EditorPage
from desktop.pages.export import ExportPage
from desktop.pages.profiles import ProfilesPage
from desktop.pages.settings import SettingsPage
from desktop.components.sidebar import Sidebar


def main(page: ft.Page):
    page.title = "Skills Manager"
    page.window.width = 1200
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.SYSTEM

    # 初始化核心
    store = SkillStore()
    state = AppState()

    # 页面
    pages = {
        "browse": BrowsePage(store, state),
        "detail": DetailPage(store, state),
        "editor": EditorPage(store, state),
        "export": ExportPage(store, state),
        "profiles": ProfilesPage(store, state),
        "settings": SettingsPage(store, state),
    }

    # 布局
    sidebar = Sidebar(state, on_navigate=lambda p: navigate(p))
    content = ft.Container(expand=True)

    def navigate(page_name: str):
        state.current_page = page_name
        content.content = pages[page_name].build()
        page.update()

    page.add(
        ft.Row(
            [sidebar.build(), ft.VerticalDivider(), content],
            expand=True,
        )
    )

    navigate("browse")


ft.app(target=main)
```

---

## 八、错误处理

### 8.1 错误分类

| 错误类型 | 说明 | 前端展示 |
| -------- | ---- | -------- |
| 解析错误 | SKILL.md 格式不合法 | 红色提示 + 具体行号 |
| 导出错误 | 适配器转换失败 | Toast 错误消息 |
| 存储错误 | 文件读写 / SQLite 错误 | Toast 错误消息 |
| 验证错误 | 参数校验失败 | 表单内联提示 |
| 网络错误 | URL / GitHub 下载失败 | Toast + 重试按钮 |
| 权限错误 | 文件系统权限不足 | 引导用户检查权限 |

### 8.2 错误恢复

- 解析错误：保留用户输入，高亮错误位置，允许手动修正
- 存储错误：自动重试一次，失败后提示用户检查磁盘空间
- 网络错误：自动重试 3 次（指数退避），失败后提示

---

## 九、构建与分发

### 9.1 开发环境

```bash
# 前置依赖
- Python 3.11+
- pip / uv / poetry

# 安装
git clone <repo>
cd skills-manager
pip install -e ".[dev]"

# 运行桌面应用
python -m desktop.main

# 运行 CLI
skills-manager export my-skill --format openai

# 运行测试
pytest tests/
```

### 9.2 平台打包分发

| 平台 | 工具 | 产物 |
| ---- | ---- | ---- |
| Windows | PyInstaller + NSIS | `.exe` 安装包 |
| macOS | PyInstaller + create-dmg | `.dmg` |
| Linux | PyInstaller + AppImage | `.AppImage` / `.deb` |

**备选方案**：Nuitka 打包，性能更好、体积更小。

### 9.3 CI/CD

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  build:
    strategy:
      matrix:
        platform: [windows-latest, macos-latest, ubuntu-latest]
    runs-on: ${{ matrix.platform }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[build]"
      - run: pyinstaller skills-manager.spec
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/*
```

---

## 十、测试策略

### 10.1 单元测试（pytest）

| 模块 | 测试内容 |
| ---- | -------- |
| parser | SKILL.md 解析：frontmatter 提取、表格解析、类型映射、枚举检测 |
| adapters | 每个适配器的输出格式正确性、边界情况（无参数、嵌套类型） |
| store | 安装、卸载、索引更新、搜索、FTS 查询 |
| profile | Profile 创建、添加/移除 Skill、导出 |
| recommend | 场景推荐匹配准确度 |
| packager | 打包、解包、文件完整性 |

### 10.2 GUI 测试

| 测试内容 | 工具 |
| -------- | ---- |
| 组件渲染 | Flet 测试工具 / 截图对比 |
| 用户交互 | 模拟点击、输入、导出操作 |
| 状态管理 | AppState 单元测试 |

### 10.3 集成测试

| 场景 | 验证方式 |
| ---- | ---- |
| 完整流程：安装 → 浏览 → 导出 | 端到端测试 |
| 多格式导出一致性 | 同一 IR 导出到 5 个格式，对比快照 |
| 大量 Skill 性能 | 1000+ Skill 列表渲染性能 |

### 10.4 示例 Skill 作为测试用例

`examples/` 目录下的每个 Skill 同时也是集成测试的 fixture。

---

## 十一、依赖清单

### 11.1 Python 依赖

```toml
[project]
name = "skills-manager"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    # 核心
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "click>=8.0",           # CLI
    "rich>=13.0",           # CLI 输出格式化

    # UI
    "flet>=0.25.0",         # 桌面 UI 框架

    # Markdown 解析
    "markdown>=3.5",
    "regex>=2024.0",

    # 存储（sqlite3 是标准库）

    # 打包（tarfile, zipfile 是标准库）

    # HTTP（远程安装）
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]
build = [
    "pyinstaller>=6.0",
    "nuitka>=2.0",          # 备选：性能更好
]
```

---

## 十二、实现优先级

### 第一步：Python 核心引擎（1-2 周）

**目标**：用 Python 快速验证核心逻辑，确认解析器 + 5 个适配器的正确性。

```text
skills-manager/
├── pyproject.toml
├── src/skills_manager/
│   ├── __init__.py
│   ├── parser.py           # SKILL.md → IR
│   ├── ir.py               # IR 数据模型（Pydantic）
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai.py
│   │   ├── claude.py
│   │   ├── gemini.py
│   │   ├── mcp.py
│   │   └── json_schema.py
│   └── cli.py              # 简单 CLI 验证
├── tests/
└── examples/
```

**验证命令**：

```bash
skills-manager export examples/translator --format openai
pytest tests/  # 全部通过
```

**交付物**：Python 包可安装，5 个格式导出正确，测试覆盖率 > 90%。

### 第二步：桌面客户端 MVP（2-3 周）

**目标**：基本可用的桌面应用。Python + Flet。

- Flet 项目脚手架
- 主界面布局（侧边栏 + 内容区）
- Skill 浏览（卡片列表 + 分类筛选）
- 搜索（实时关键词）
- Skill 详情（参数表、示例、文档）
- 导出面板（格式选择 → 预览 → 复制/保存）
- 批量导出
- 安装 / 卸载
- 新建 Skill（骨架生成）
- 暗色 / 亮色主题
- 错误处理 + Toast

**交付物**：可安装运行的桌面应用，核心流程（浏览 → 导出）跑通。

### 第三步：编辑器与增强（2-3 周）

- 内置 Markdown 编辑器
- 实时解析预览（编辑 SKILL.md → 即时显示 IR）
- 语法校验（frontmatter 格式、参数表格式）
- Profile 管理（创建 / 编辑 / 导出）
- 拖拽式 Profile 配置
- 从 URL / GitHub 安装
- 场景推荐
- 导出历史
- 全局快捷键
- 设置页

**交付物**：功能完整的桌面应用，覆盖任务书 80% 功能。

### 第 3.5 步：Rust 性能优化（2-3 周，可选）

**目标**：将性能关键路径移植到 Rust。仅在 profiling 证明 Python 是瓶颈时执行。

- 对 Python 引擎做性能分析，定位瓶颈
- 通过 PyO3/maturin 实现 Rust 解析器 + 适配器
- 作为 Python 扩展模块 drop-in 替换（同 API）
- 基准测试：Python vs Rust 在 1000+ Skill 下的表现
- 桌面应用透明使用 Rust 扩展（用户无感知）
- Rust 扩展与 Python 应用一起打包

**交付物**：可选的 Rust 核心引擎。桌面应用从用户角度无变化。

> **关键原则**：Rust 是可选的性能升级，不是重写。Python 代码库始终是 source of truth。如果 Python 性能够用，完全可以跳过。

### 第四步：打磨与发布（2 周）

- Windows `.exe` 安装包（PyInstaller）
- macOS `.dmg` 安装包
- Linux `.AppImage` / `.deb` 安装包
- 自动更新机制
- 文档和用户指南
- 5+ 示例 Skill
- 性能优化（虚拟滚动）
- 边界情况完善
- PyPI 发布 CLI 工具

**交付物**：v1.0 正式发布。
