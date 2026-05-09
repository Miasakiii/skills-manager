# Skills Manager

> 用一种极简格式定义 AI Skill，一键导出为 OpenAI / Claude / Gemini / MCP 等主流平台格式。

## 核心理念

**不要做 Skill 的 npm，做 Skill 的 babel。**

AI Agent 生态的工具格式碎片化，同一个能力要在每个平台手写一遍定义。Skills Manager 让你只写一次，到处导出。

## 快速开始

### 1. 写一个 Skill（5 分钟）

创建 `my-skill/SKILL.md`：

```markdown
---
name: hello
version: "1.0.0"
description: 一个简单的问候工具
---

## 功能

向用户打招呼。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| name | string | ✅ | 用户名称 |
| language | string | ❌ | 语言：zh / en，默认 zh |
```

### 2. 导出

```bash
# 导出为 OpenAI Function Calling 格式
skills-manager export hello --format openai

# 导出为 Claude Tool Use 格式
skills-manager export hello --format claude

# 导出为可运行的 MCP Server
skills-manager export hello --format mcp --output hello_mcp.py
```

### 3. 使用

将导出的 JSON 直接粘贴到你的 Agent 代码中，零修改。

## 安装

```bash
pip install skills-manager
```

## 命令速查

```bash
# Skill 管理
skills-manager install <source>              # 安装（目录 / .skill / URL / gh:user/repo）
skills-manager uninstall <name>              # 卸载
skills-manager list                          # 列出已安装
skills-manager info <name>                   # 查看详情

# 浏览与推荐
skills-manager browse [--category <cat>]     # 按分类浏览
skills-manager search <query>                # 关键词搜索
skills-manager recommend <场景描述>           # 根据场景推荐 Skill

# Agent 分发
skills-manager profile create <name>         # 创建 Agent Profile
skills-manager profile add <profile> <skill> # 添加 Skill 到 Profile
skills-manager profile export <profile> --format openai  # 导出给 Agent 使用

# 格式导出
skills-manager export <name> --format openai|claude|gemini|mcp|schema
skills-manager export --all --format openai  # 批量导出

# 打包
skills-manager pack <dir>                    # 打包为 .skill 文件

# 工具
skills-manager doctor                        # 环境检查
skills-manager init                          # 初始化 ~/.skills-manager/
```

## 项目结构

```
skills-manager/
├── task-book.md                        # 项目目标、范围、路线图
├── tech-design.md                      # 格式规范、架构、实现细节
├── src/skills_manager/                 # 核心引擎（Python）
├── desktop/                            # Flet 桌面应用
├── examples/                           # 示例 Skills
│   ├── translator/                     # 完整 Tool Skill 示例
│   ├── json-formatter/                 # 纯 Python 工具示例
│   └── code-reviewer/                  # Prompt Skill 示例
└── tests/
```

## 技术栈

| 层面 | 选择 |
| ---- | ---- |
| 语言 | Python 3.11+ |
| UI 框架 | Flet（基于 Flutter） |
| 数据模型 | Pydantic |
| 存储 | SQLite |
| CLI | Click |
| 打包 | PyInstaller / Nuitka |

## 文档

- [任务书](./task-book.md) — 解决什么问题、做什么不做什么、路线图
- [技术设计文档](./tech-design.md) — 格式规范、IR、适配器、CLI、存储、实现细节

## 许可

MIT
