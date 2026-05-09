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
skills-manager install <source>              # 安装（目录 / .skill 包）
skills-manager install-url <url>             # 从 URL / GitHub 安装
skills-manager uninstall <name>              # 卸载
skills-manager list                          # 列出已安装
skills-manager info <name>                   # 查看详情
skills-manager search <query>                # 关键词搜索

# 版本管理
skills-manager upgrade <name>                # 从原始来源更新
skills-manager rollback <name>               # 回滚到上一版本
skills-manager history <name>                # 查看版本历史

# 格式导出
skills-manager export <name> --format openai|claude|gemini|mcp|schema
skills-manager export --all --format openai  # 批量导出

# 打包
skills-manager pack <dir>                    # 打包为 .skill 文件

# 工具
skills-manager doctor                        # 环境检查
```

## 桌面应用

基于 Flet 构建的跨平台桌面客户端，提供可视化管理体验：

```bash
cd skills-manager-prototype/desktop
python main.py
```

功能：

- 卡片式浏览、分类筛选、关键词搜索
- 一键导出到 5 种平台格式
- 内置编辑器，实时预览和语法校验
- 批量导入、批量导出
- Profile 管理（Agent Skill 组合）
- 场景推荐引擎
- 版本管理（升级 / 回滚 / 历史）
- 从 URL / GitHub 安装
- 导出历史记录
- 全局快捷键

## 项目结构

```
skills-manager/
├── task-book.md                        # 项目目标、范围、路线图
├── tech-design.md                      # 格式规范、架构、实现细节
├── src/skills_manager/                 # 核心引擎（Python）
│   ├── parser.py                       # SKILL.md 解析器
│   ├── ir.py                           # 中间表示（IR）
│   ├── adapters/                       # 格式适配器
│   ├── store.py                        # 本地存储管理
│   ├── validator.py                    # 格式验证器
│   ├── recommend.py                    # 场景推荐引擎
│   ├── packager.py                     # 打包/解包
│   └── cli.py                          # CLI 入口
├── desktop/                            # Flet 桌面应用
│   ├── app.py                          # 主控逻辑
│   ├── pages/                          # 页面模块
│   ├── components.py                   # 通用组件
│   └── dialogs.py                      # 对话框
├── examples/                           # 示例 Skills（6 个）
│   ├── translator/                     # 多语言翻译
│   ├── code-reviewer/                  # 代码审查
│   ├── code-generator/                 # 代码生成
│   ├── json-formatter/                 # JSON 格式化
│   ├── deploy-pipeline/                # 部署流水线
│   └── interview-prep/                 # 面试准备
└── tests/                              # 测试（196 个，100% 通过）
```

## 技术栈

| 层面 | 选择 |
| ---- | ---- |
| 语言 | Python 3.11+ |
| UI 框架 | Flet 0.84（基于 Flutter） |
| 数据模型 | Python dataclass |
| 存储 | JSON 文件索引 |
| CLI | typer + rich |
| 打包 | PyInstaller / Nuitka |

## 文档

- [任务书](./task-book.md) — 解决什么问题、做什么不做什么、路线图
- [技术设计文档](./tech-design.md) — 格式规范、IR、适配器、CLI、存储、实现细节

## 许可

MIT
