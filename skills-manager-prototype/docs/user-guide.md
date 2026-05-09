# Skills Manager 用户指南

> 本指南帮助你快速上手 Skills Manager，从创建第一个 Skill 到导出为各种平台格式。

## 目录

1. [快速开始](#快速开始)
2. [创建 Skill](#创建-skill)
3. [安装 Skill](#安装-skill)
4. [使用桌面应用](#使用桌面应用)
5. [使用 CLI](#使用-cli)
6. [导出格式](#导出格式)
7. [高级功能](#高级功能)
8. [常见问题](#常见问题)

---

## 快速开始

### 安装 Skills Manager

```bash
# 从源码安装
git clone <repo-url>
cd skills-manager-prototype
pip install -e ".[dev]"
```

### 创建你的第一个 Skill

1. 创建目录 `my-first-skill/`
2. 在目录中创建 `SKILL.md` 文件
3. 填写内容（参考下方模板）

````markdown
---
name: hello-world
version: "1.0.0"
description: 一个简单的问候工具
summary: 向用户打招呼，支持中英文。
skill_type: component
---

## 功能

向用户打招呼。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| name | string | ✅ | 用户名称 |
| language | string | ❌ | 语言：zh / en，默认 zh |

## 示例

输入：
````json
{"name": "世界", "language": "zh"}
````

输出：
````json
{"greeting": "你好，世界！"}
````
````

### 安装并导出

```bash
# 安装
skills-manager install ./my-first-skill

# 查看
skills-manager info hello-world

# 导出为 OpenAI 格式
skills-manager export hello-world --format openai
```

---

## 创建 Skill

### SKILL.md 结构

一个完整的 SKILL.md 包含两部分：

1. **Frontmatter**（YAML 格式）— 机器可读的元数据
2. **Markdown Body** — 人类可读的文档

### Frontmatter 字段

#### 必填字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| name | string | 唯一标识，小写 + 连字符 | `translator` |
| version | string | 语义化版本 | `"1.0.0"` |
| description | string | 一句话描述（< 200 字） | `多语言翻译工具` |
| summary | string | 2-3 句话摘要 | 支持多行文本 |

#### 可选字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| skill_type | string | 语义类型 | `component` / `interactive` / `workflow` |
| intent | string | 详细意图说明 | `引导用户完成翻译任务` |
| tags | list | 自由标签 | `[translation, i18n]` |
| category | string | 一级分类标识 | `language` |
| executor | dict | 执行配置 | 见下方 |
| security | dict | 安全声明 | 见下方 |
| author | string | 作者 | `someone` |
| license | string | 许可证 | `MIT` |

#### skill_type 语义类型

| 类型 | 说明 | 示例 |
|------|------|------|
| component | 模板/制品（填空式产出） | 翻译工具、格式化器 |
| interactive | 引导式对话（多轮问答） | 需求分析、面试准备 |
| workflow | 端到端流程（多阶段编排） | 部署流程、CI/CD |

#### executor 执行配置

```yaml
executor:
  type: python          # python | node | shell | http
  entry: handler.py     # 入口文件
  function: translate   # 入口函数名
```

#### security 安全声明

```yaml
security:
  needs_network: true   # 是否需要网络
  needs_api_key: true   # 是否需要 API Key
```

### Markdown Body 章节

| 章节 | 必填 | 说明 |
|------|------|------|
| 功能 | 推荐 | 详细描述 Skill 的功能 |
| 参数 | 推荐 | 参数表格（Markdown 表格格式） |
| 返回 | 可选 | 返回值表格 |
| 示例 | 推荐 | 输入输出示例（JSON 格式） |
| 适用场景 | 推荐 | 使用场景列表 |
| 不适用 | 推荐 | 不适用场景列表 |

### 参数表格格式

````markdown
## 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| text | string | ✅ | 待翻译文本 |
| target_lang | string | ✅ | 目标语言：zh / en / ja / ko |
| style | string | ❌ | 风格：formal / casual / technical |
````

**类型支持**：
- `string` — 字符串
- `integer` / `int` — 整数
- `number` / `float` — 浮点数
- `boolean` / `bool` — 布尔值
- `array` — 数组
- `object` — 对象

**必需标记**：
- `✅` / `是` / `yes` / `true` — 必填
- `❌` / `否` / `no` / `false` — 可选

**枚举值检测**：
在说明中使用 `X / Y / Z` 格式，会自动提取为枚举值。

### 示例章节格式

````markdown
## 示例

输入：
```json
{"text": "Hello", "target_lang": "zh"}
```

输出：
```json
{"translated_text": "你好"}
```
````

---

## 安装 Skill

### 从目录安装

```bash
skills-manager install ./my-skill
```

### 从 .skill 包安装

```bash
skills-manager install my-skill-1.0.0.skill
```

### 自动扫描安装

桌面应用支持自动扫描预设路径：
- `~/.cc-switch/skills/`
- `~/.claude/skills/`
- `~/.codex/skills/`
- `~/.gemini/skills/`
- 其他 agent 工具目录

### 强制覆盖安装

```bash
skills-manager install ./my-skill --force
```

### 卸载 Skill

```bash
skills-manager uninstall my-skill
```

---

## 使用桌面应用

### 启动应用

```bash
python -m desktop.main
```

### 主界面

```
┌─────────────────────────────────────────────────────────────┐
│  ┌──────────┐  ┌──────────────────────────────────────────┐ │
│  │          │  │                                          │ │
│  │  侧边栏   │  │              内容区                      │ │
│  │          │  │                                          │ │
│  │ 📋 浏览   │  │  ┌──────────────────────────────────┐  │ │
│  │ 📤 导出   │  │  │        Skill 卡片网格             │  │ │
│  │ 📝 编辑器 │  │  │                                  │  │ │
│  │ ⚙️ 设置   │  │  │  ┌──────┐ ┌──────┐ ┌──────┐    │  │ │
│  │          │  │  │  │Card 1│ │Card 2│ │Card 3│    │  │ │
│  └──────────┘  │  │  └──────┘ └──────┘ └──────┘    │  │ │
│                │  └──────────────────────────────────┘  │ │
│                └──────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 浏览页

- **搜索**：输入关键词实时过滤
- **类型筛选**：点击芯片筛选 component / interactive / workflow
- **查看详情**：点击卡片进入详情页

### 详情页

- **参数表**：查看 Skill 的参数定义
- **示例**：查看输入输出示例
- **导出**：选择格式导出

### 导出页

1. 选择要导出的 Skill（多选）
2. 选择导出格式（openai / claude / gemini / mcp / schema）
3. 选择打包格式（可选：Claude Desktop / Codex / Claude Code）
4. 选择输出目录
5. 点击"导出选中"或"打包选中"

### 设置页

- **主题切换**：浅色 / 深色
- **默认导出格式**：设置默认格式
- **存储信息**：查看存储路径和 Skill 数量
- **监视路径**：管理自动扫描路径
- **同步到 Agent**：重新同步所有 Skill 到 agent 目录

---

## 使用 CLI

### 基本命令

```bash
# 查看帮助
skills-manager --help

# 列出已安装
skills-manager list

# 查看详情
skills-manager info <name>

# 搜索
skills-manager search <query>
```

### 导出命令

```bash
# 导出单个 Skill
skills-manager export <name> --format <format>

# 导出到文件
skills-manager export <name> --format openai --output ./output/

# 批量导出
skills-manager export --all --format openai
```

### 安装命令

```bash
# 从目录安装
skills-manager install <path>

# 从 .skill 包安装
skills-manager install <package.skill>

# 强制覆盖
skills-manager install <path> --force
```

### 打包命令

```bash
# 打包为 .skill 文件
skills-manager pack <directory>
```

---

## 导出格式

### OpenAI Function Calling

```json
{
  "type": "function",
  "function": {
    "name": "translator",
    "description": "多语言翻译工具",
    "parameters": {
      "type": "object",
      "properties": {
        "text": {"type": "string", "description": "待翻译文本"},
        "target_lang": {"type": "string", "description": "目标语言"}
      },
      "required": ["text", "target_lang"]
    }
  }
}
```

### Claude Tool Use

```json
{
  "name": "translator",
  "description": "多语言翻译工具",
  "input_schema": {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "待翻译文本"},
      "target_lang": {"type": "string", "description": "目标语言"}
    },
    "required": ["text", "target_lang"]
  }
}
```

### Gemini Function Declaration

```json
{
  "function_declarations": [
    {
      "name": "translator",
      "description": "多语言翻译工具",
      "parameters": {
        "type": "OBJECT",
        "properties": {
          "text": {"type": "STRING", "description": "待翻译文本"},
          "target_lang": {"type": "STRING", "description": "目标语言"}
        },
        "required": ["text", "target_lang"]
      }
    }
  ]
}
```

### MCP Server

生成可直接运行的 Python 脚本：

```python
#!/usr/bin/env python3
"""MCP Server for translator - 多语言翻译工具"""
from mcp.server import Server
from mcp.types import Tool
import json

server = Server("translator")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="translator",
            description="多语言翻译工具",
            inputSchema={...}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    from handler import translate
    return translate(**arguments)

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read, write):
            await server.run(read, write)

    asyncio.run(main())
```

### JSON Schema

```json
{
  "type": "object",
  "properties": {
    "text": {"type": "string", "description": "待翻译文本"},
    "target_lang": {"type": "string", "description": "目标语言"}
  },
  "required": ["text", "target_lang"]
}
```

---

## 高级功能

### 平台打包

将 Skill 打包为特定平台格式：

```bash
# 在桌面应用中
# 1. 选择 Skill
# 2. 选择打包格式（Claude Desktop / Codex / Claude Code）
# 3. 选择输出目录
# 4. 点击"打包选中"
```

**打包格式说明**：

| 格式 | 说明 | 用途 |
|------|------|------|
| Claude Desktop | ZIP，含 Skill.md 副本 | 导入 Claude Desktop |
| Codex | ZIP，含 AGENTS.md 和 .agents/skills/ 结构 | 导入 Codex |
| Claude Code | ZIP，含 .claude/skills/ 结构 | 导入 Claude Code |

### 自动同步

安装 Skill 后，会自动创建 symlink 到各 agent 目录：
- `~/.claude/skills/`
- `~/.codex/skills/`
- `~/.gemini/skills/`
- 其他已存在的 agent 目录

### 监视路径

在设置页添加自定义监视路径，自动扫描发现新 Skill。

### CLAUDE.md 生成

安装 Skill 后，可自动生成 CLAUDE.md 文件，让 agent 知道有哪些 Skill 可用。

---

## 常见问题

### Q: 安装时提示"验证失败"

A: 检查 SKILL.md 格式是否正确：
- 必须有 YAML frontmatter（以 `---` 开头和结尾）
- 必须有 `name` 和 `description` 字段
- YAML 语法是否正确

### Q: 导出的 JSON 格式不对

A: 检查参数表格格式：
- 表头必须是 `| 参数 | 类型 | 必需 | 说明 |`
- 分隔行必须是 `|---|---|---|---|`
- 每行必须有相同数量的列

### Q: 桌面应用启动失败

A: 检查：
1. Python 版本 >= 3.11
2. 依赖是否安装完整：`pip install -e ".[dev]"`
3. Flet 版本是否正确

### Q: 如何添加新的导出格式

A: 参考 `src/skills_manager/adapters/` 目录，继承 `BaseAdapter` 类，实现 `export` 方法。

### Q: Skill 文件存放在哪里

A: 默认存放在 `~/.skills-manager/store/` 目录下，每个 Skill 一个子目录。

### Q: 如何备份 Skill

A: 使用打包功能：
```bash
skills-manager pack ~/.skills-manager/store/my-skill
```

---

## 获取帮助

- 查看 `skills-manager --help`
- 查看 [README.md](../README.md)
- 查看 [技术设计文档](../../tech-design.md)
- 提交 Issue 到 GitHub

---

## 示例 Skill

参考 `examples/` 目录：

- `translator/` — 翻译工具（component 类型）
- `json-formatter/` — JSON 格式化（component 类型）
- `code-reviewer` — 代码审查（component 类型）

---

## 最佳实践

### Skill 命名规范

- 使用小写字母和连字符：`my-skill`（不是 `my_skill` 或 `MySkill`）
- 名称简洁明了：`translator`（不是 `translation-tool-for-text`）
- 避免保留字：`export`、`import`、`test` 等

### 版本管理

- 使用语义化版本：`主版本.次版本.修订版本`
- 破坏性变更递增主版本：`1.0.0` → `2.0.0`
- 新功能递增次版本：`1.0.0` → `1.1.0`
- Bug 修复递增修订版本：`1.0.0` → `1.0.1`

### 参数设计

- 必填参数放前面，可选参数放后面
- 提供合理的默认值
- 使用枚举值限制选项：`style: formal / casual / technical`

### 文档编写

- `description`：一句话说明，< 200 字
- `summary`：2-3 句话，支持多行
- `功能`：详细描述，包括边界情况
- `示例`：提供输入输出示例，便于理解

---

## 高级用法

### 批量操作

```bash
# 批量导出所有 Skill
skills-manager export --all --format openai --output ./dist/

# 批量安装
skills-manager install ./skills-dir --force
```

### 高级用法：自动同步

安装 Skill 后，会自动创建 symlink 到已存在的 agent 目录：

- `~/.claude/skills/`
- `~/.codex/skills/`
- `~/.gemini/skills/`

### 高级用法：监视路径

在设置页添加监视路径，自动扫描发现新 Skill：

1. 打开设置页
2. 添加监视路径（如 `~/my-skills/`）
3. 点击"扫描"按钮
4. 发现的 Skill 会显示在列表中

### 高级用法：打包分享

将 Skill 打包为平台特定格式，方便分享：

```bash
# Claude Desktop 格式
skills-manager pack ./my-skill --format claude-desktop

# Codex 格式
skills-manager pack ./my-skill --format codex

# Claude Code 格式
skills-manager pack ./my-skill --format claude-code
```

---

## 故障排除

### 常见错误

| 错误信息 | 原因 | 解决方案 |
| ---- | ---- | ---- |
| `验证失败: 缺少必填字段: name` | SKILL.md 缺少 name 字段 | 添加 `name: my-skill` |
| `验证失败: YAML 解析失败` | YAML 语法错误 | 检查缩进和特殊字符 |
| `Skill already installed` | 同名 Skill 已存在 | 使用 `--force` 覆盖 |
| `导出失败: 未知格式` | 不支持的导出格式 | 使用 openai/claude/gemini/mcp/schema |

### 调试技巧

1. **查看详细日志**：使用 `--verbose` 参数
2. **验证 SKILL.md**：`skills-manager doctor`
3. **检查安装状态**：`skills-manager list`
4. **测试导出**：`skills-manager export <name> --format openai`

### 性能优化

- 大量 Skill 时，使用关键词搜索而非全量浏览
- 批量导出时，选择特定格式而非全部格式
- 定期清理不需要的 Skill：`skills-manager uninstall <name>`

---

## 贡献指南

### 添加新适配器

1. 在 `src/skills_manager/adapters/` 创建新文件
2. 继承 `BaseAdapter` 类
3. 实现 `name`、`file_extension`、`export` 方法
4. 在 `__init__.py` 注册适配器
5. 添加测试用例

### 添加新验证规则

1. 在 `src/skills_manager/validator.py` 添加规则
2. 返回 `ValidationResult`（errors 或 warnings）
3. 添加测试用例

### 代码质量

```bash
# 格式化
ruff format .

# 检查
ruff check .

# 类型检查
mypy src/

# 测试
pytest tests/ --cov=skills_manager
```
