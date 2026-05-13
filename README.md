# Skills Manager v0.1.4

> 写一次 AI Skill 定义，一键导出为 OpenAI / Claude / Gemini / MCP 等主流平台格式。

[![PyPI](https://img.shields.io/pypi/v/skillfmt)](https://pypi.org/project/skillfmt/)
[![Test](https://img.shields.io/badge/tests-271%20passed-green)](https://github.com/Miasakiii/skills-manager)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## 快速安装

### PyPI（推荐）

```bash
pip install skillfmt
```

### 桌面应用 / 独立可执行文件

从 [Releases](https://github.com/Miasakiii/skills-manager/releases/latest) 下载对应平台安装包：

| 平台 | 安装包 | 说明 |
|------|--------|------|
| Windows | `skills-manager-setup-windows.exe` | 安装向导（推荐） |
| Windows | `skills-manager-desktop.exe` | 绿色版桌面应用 |
| Windows | `skills-manager-cli.exe` | 绿色版 CLI |
| macOS | `skills-manager-desktop.dmg` | 桌面应用 |

> Linux 桌面版暂未提供预编译包，请使用 `pip install skillfmt` 或从源码运行。

## 快速开始

### 1. 创建一个 Skill

创建目录 `my-skill/`，在其中创建 `SKILL.md`：

~~~text
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
| name | string | 是 | 用户名称 |
| language | string | 否 | 语言：zh / en，默认 zh |

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
~~~

### 2. 安装并导出

```bash
# 安装 Skill
skillfmt install ./my-skill

# 导出为 OpenAI 格式
skillfmt export hello --format openai

# 导出为 Claude 格式
skillfmt export hello --format claude

# 导出为 MCP Server
skillfmt export hello --format mcp --output hello_mcp.py
```

### 3. 桌面应用

从 [Releases](https://github.com/Miasakiii/skills-manager/releases/latest) 下载安装包，或从源码运行：

```bash
cd skills-manager-prototype
python -m desktop
```

### 4. 启动 Server（MCP / HTTP API）

```bash
# MCP 模式（stdio，供 Claude Desktop 等调用）
pip install skillfmt[server]
skillfmt serve --mode mcp

# HTTP API 模式
skillfmt serve --mode api --port 8000
```

### 5. 检查更新

```bash
skillfmt check-update
```

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

~~~text
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
~~~

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
skills-manager/
├── skills-manager-prototype/    # 项目源码
│   ├── src/skills_manager/      # 核心引擎
│   │   ├── cli.py               # CLI 入口
│   │   ├── parser.py            # SKILL.md 解析器
│   │   ├── store/               # 本地存储（安装/索引/搜索/同步）
│   │   ├── adapters/            # 格式适配器（OpenAI / Claude / Gemini / MCP）
│   │   ├── server/              # MCP Server + HTTP API
│   │   └── ...
│   ├── desktop/                 # 桌面客户端（Flet）
│   ├── examples/                # 示例 Skills
│   ├── tests/                   # 测试
│   ├── docs/                    # 文档
│   └── pyproject.toml           # 项目配置
├── .github/workflows/           # CI/CD
│   ├── ci.yml                   # 测试 + lint
│   └── release.yml              # 三平台构建 + PyPI 发布
├── CHANGELOG.md                 # 变更记录
└── README.md                    # 本文件
```

## 开发指南

### 运行测试

```bash
cd skills-manager-prototype

# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_parser.py -v

# 查看覆盖率
pytest tests/ --cov=skills_manager --cov-report=term-missing
```

### 代码质量

```bash
cd skills-manager-prototype

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

- [用户指南](skills-manager-prototype/docs/user-guide.md)：详细使用说明
- [CHANGELOG](CHANGELOG.md)：版本变更记录

## 许可

MIT
