# Skills Manager

> 用一种极简格式定义 AI Skill，一键导出为 OpenAI / Claude / Gemini / MCP 等主流平台格式。

## 核心理念

**不要做 Skill 的 npm，做 Skill 的 babel。**

AI Agent 生态的工具格式碎片化，同一个能力要在每个平台手写一遍定义。Skills Manager 让你只写一次，到处导出。

## 项目状态

- **测试覆盖率**：92%
- **测试数量**：144 个（全部通过）
- **支持格式**：5 种（OpenAI / Claude / Gemini / MCP / JSON Schema）
- **平台打包**：3 种（Claude Desktop / Codex / Claude Code）

## 功能特性

### 核心功能

- **格式转换**：一份定义 → 多平台格式（OpenAI / Claude / Gemini / MCP / JSON Schema）
- **可视化管理**：桌面客户端提供直观的 Skill 浏览、搜索、编辑和导出体验
- **本地管理**：所有 Skill 统一存储，安装、搜索、查看一条命令或一次点击搞定
- **自动同步**：安装后自动 symlink 到各 agent 目录，agent 立即可用
- **格式验证**：安装前自动验证 SKILL.md 格式，确保合规

### 桌面客户端

- **Skill 浏览**：卡片式浏览、分类筛选、关键词搜索
- **类型筛选**：按 component / interactive / workflow 语义类型筛选
- **一键导出**：选中 Skill → 选择目标平台 → 复制或保存
- **批量导出**：多选 Skill 批量导出
- **平台打包**：导出为 Claude Desktop / Codex / Claude Code 平台格式
- **安装管理**：从目录、.skill 包、自动扫描导入
- **主题切换**：浅色 / 深色主题
- **监视路径**：自定义扫描路径

### CLI 工具

```bash
# Skill 管理
skills-manager install <source>              # 安装（目录 / .skill 包）
skills-manager uninstall <name>              # 卸载
skills-manager list                          # 列出已安装
skills-manager info <name>                   # 查看详情

# 格式导出
skills-manager export <name> --format openai|claude|gemini|mcp|schema
skills-manager export --all --format openai  # 批量导出

# 打包
skills-manager pack <dir>                    # 打包为 .skill 文件
```

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone <repo-url>
cd skills-manager-prototype

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -e ".[dev]"
```

### 运行桌面应用

```bash
python -m desktop.main
```

### 运行 CLI

```bash
skills-manager --help
```

## 快速开始

### 1. 创建一个 Skill

创建目录 `my-skill/`，在其中创建 `SKILL.md`：

```markdown
---
name: hello
version: "1.0.0"
description: 一个简单的问候工具
summary: 向用户打招呼，支持中英文。
skill_type: component
intent: 用于测试和演示的简单问候工具
tags: [demo, greeting]
category: misc
---

## 功能

向用户打招呼。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| name | string | ✅ | 用户名称 |
| language | string | ❌ | 语言：zh / en，默认 zh |

## 示例

```json
{"name": "世界", "language": "zh"}
```

```json
{"greeting": "你好，世界！"}
```

## 适用场景

- 测试 Skill 系统
- 演示基本功能

## 不适用

- 生产环境使用
```

### 2. 安装 Skill

```bash
# 从目录安装
skills-manager install ./my-skill

# 或使用桌面应用
# 点击侧边栏"安装 Skill" → 选择目录
```

### 3. 导出 Skill

```bash
# 导出为 OpenAI 格式
skills-manager export hello --format openai

# 导出为 Claude 格式
skills-manager export hello --format claude

# 导出为 MCP Server
skills-manager export hello --format mcp --output hello_mcp.py
```

### 4. 使用桌面应用

```bash
python -m desktop.main
```

在桌面应用中：
1. 浏览已安装的 Skill
2. 点击 Skill 查看详情
3. 选择格式导出
4. 或批量导出多个 Skill

## SKILL.md 格式规范

### Frontmatter（必填）

```yaml
---
name: skill-name          # 必填：唯一标识，小写 + 连字符
version: "1.0.0"          # 必填：语义化版本
description: 一句话描述    # 必填：简短描述（< 200 字）
summary: |                # 必填：2-3 句话摘要
  详细描述这个 Skill 的功能。
  支持多行文本。
---
```

### Frontmatter（可选）

```yaml
---
# 语义类型
skill_type: component     # component | interactive | workflow
intent: 详细意图说明       # 这个 Skill 要解决什么问题

# 分类
tags: [tag1, tag2]        # 自由标签
category: language        # 一级分类标识

# 执行配置
executor:
  type: python            # python | node | shell | http
  entry: handler.py       # 入口文件
  function: translate     # 入口函数名

# 安全声明
security:
  needs_network: true
  needs_api_key: true

# 元信息
author: someone
license: MIT
---
```

### Markdown Body

```markdown
## 功能

详细描述 Skill 的功能。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| param1 | string | ✅ | 参数说明 |
| param2 | integer | ❌ | 可选参数 |

## 返回

| 字段 | 类型 | 说明 |
|------|------|------|
| result | string | 返回结果 |

## 示例

输入：
```json
{"param1": "value"}
```

输出：
```json
{"result": "processed"}
```

## 适用场景

- 场景 1
- 场景 2

## 不适用

- 不适用场景 1
```

## 支持的导出格式

| 格式 | 说明 | 文件扩展名 |
|------|------|-----------|
| openai | OpenAI Function Calling | .json |
| claude | Claude Tool Use | .json |
| gemini | Gemini Function Declaration | .json |
| mcp | MCP Server（可运行） | .py |
| schema | JSON Schema | .json |

## 项目结构

```
skills-manager-prototype/
├── README.md                           # 本文件
├── IMPROVEMENTS.md                     # 改进计划
├── pyproject.toml                      # 项目配置
├── src/skills_manager/                 # 核心引擎
│   ├── __init__.py
│   ├── ir.py                           # 中间表示（IR）
│   ├── parser.py                       # SKILL.md 解析器
│   ├── store.py                        # 本地存储管理
│   ├── validator.py                    # 格式验证器
│   ├── packager.py                     # 打包器
│   ├── agent_config.py                 # Agent 配置生成
│   ├── cli.py                          # CLI 入口
│   └── adapters/                       # 格式适配器
│       ├── base.py                     # 适配器基类
│       ├── openai.py                   # OpenAI 适配器
│       ├── claude.py                   # Claude 适配器
│       ├── gemini.py                   # Gemini 适配器
│       ├── mcp.py                      # MCP 适配器
│       └── json_schema.py             # JSON Schema 适配器
├── desktop/                            # 桌面客户端（Flet）
│   ├── main.py                         # 入口
│   ├── app.py                          # 主控类
│   ├── components.py                   # 可复用组件
│   ├── dialogs.py                      # 对话框
│   └── pages/                          # 页面
│       ├── browse.py                   # 浏览页
│       ├── detail.py                   # 详情页
│       ├── export.py                   # 导出页
│       ├── editor.py                   # 编辑器页
│       └── settings.py                 # 设置页
├── examples/                           # 示例 Skills
│   ├── translator/                     # 翻译工具（component）
│   ├── json-formatter/                 # JSON 格式化（component）
│   ├── code-reviewer/                  # 代码审查（component）
│   ├── interview-prep/                 # 面试准备（interactive）
│   ├── deploy-pipeline/                # 部署流程（workflow）
│   └── code-generator/                 # 代码生成（component）
└── tests/                              # 测试
    ├── test_parser.py
    ├── test_adapters.py
    ├── test_store.py
    ├── test_validator.py
    ├── test_packager.py
    ├── test_agent_config.py
    └── test_cli.py
```

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_parser.py -v

# 查看覆盖率
pytest tests/ --cov=skills_manager --cov-report=term-missing
```

### 代码质量

```bash
# 格式化
ruff format .

# 检查
ruff check .

# 类型检查
mypy src/
```

### 添加新适配器

1. 在 `src/skills_manager/adapters/` 创建新文件
2. 继承 `BaseAdapter` 类
3. 实现 `name`、`file_extension`、`export` 方法
4. 在 `__init__.py` 注册适配器
5. 添加测试

### 添加新验证规则

1. 在 `src/skills_manager/validator.py` 添加规则
2. 返回 `ValidationResult`（errors 或 warnings）
3. 添加测试用例

## 文档

- [任务书](../task-book.md) — 解决什么问题、做什么不做什么、路线图
- [技术设计文档](../tech-design.md) — 格式规范、IR、适配器、CLI、存储、实现细节
- [改进计划](./IMPROVEMENTS.md) — 参考 Product Manager Skills 的改进方向
- [用户指南](./docs/user-guide.md) — 详细使用说明

## 许可

MIT
