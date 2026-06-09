# 竞品分析：xingkongliang/skills-manager

> 调研日期：2026-06-09
> 仓库地址：https://github.com/xingkongliang/skills-manager

## 基本信息

| 指标       | 值                                                                                              |
| ---------- | ----------------------------------------------------------------------------------------------- |
| ⭐ Stars   | 2,052                                                                                           |
| 🍴 Forks   | 183                                                                                             |
| 📅 创建    | 2026-03-02                                                                                      |
| 📄 License | MIT                                                                                             |
| 🔤 主语言  | Rust + TypeScript                                                                               |
| 📦 技术栈  | Tauri 2 + React 19 + TypeScript + Tailwind CSS + SQLite (`rusqlite`) + react-i18next            |
| 🎯 定位    | 轻量桌面应用，跨 15+ AI 编程工具统一管理、同步、组织 agent skills                               |

## 项目概述

Skills Manager 是一个跨平台桌面应用，核心理念是"一个应用管理所有 AI agent 的 skills"。它将来自 Git 仓库、本地文件夹、`.zip`/`.skill` 压缩包、以及 [skills.sh](https://skills.sh) 市场的技能统一收入一个中央仓库（默认 `~/.skills-manager`），然后通过 symlink 或 copy 同步到各个 agent 的技能目录。

### 支持的工具（15+）

Cursor · Claude Code · Codex · Grok · OpenCode · Amp · Kilo Code · Roo Code · Goose · Gemini CLI · GitHub Copilot · Windsurf · TRAE IDE · Antigravity · Clawdbot · Droid

用户还可以在 Settings 中自定义添加其他工具。

## 架构设计

### 技术架构

```
┌─────────────────────────────────────────────┐
│              Frontend (React 19)             │
│         TypeScript + Vite + Tailwind CSS     │
├─────────────────────────────────────────────┤
│             Tauri 2 (Desktop Shell)          │
├─────────────────────────────────────────────┤
│           Rust Backend (Shared Core)         │
│    ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│    │  SQLite   │  │  Sync    │  │  Git    │  │
│    │  Store    │  │  Engine  │  │  Module │  │
│    └──────────┘  └──────────┘  └─────────┘  │
├──────────────────┬──────────────────────────┤
│   Desktop App    │         CLI              │
│   (Tauri)        │   (同一 Rust 核心)        │
└──────────────────┴──────────────────────────┘
```

**关键设计决策：**

- **Rust 共享核心** — 桌面端和 CLI 共用同一个 Rust 核心层，SQLite 数据库、同步引擎、Git 模块完全复用，避免逻辑分叉
- **SQLite 元数据存储** — 技能元数据存储在 SQLite 中，不纳入 Git；数据库可从技能文件扫描重建
- **i18n 内置** — 使用 react-i18next 支持中英文

### 核心概念模型

```
Library (中央仓库 ~/.skills-manager/skills/)
  ├── Skill A
  ├── Skill B
  └── Skill C

Preset (技能预设组)
  ├── "Web Dev"  → [Skill A, Skill B]
  └── "Data"     → [Skill B, Skill C]

Global Workspace (每个 agent 的全局技能目录)
  ├── Claude Code  → ~/.claude/skills/
  ├── Cursor       → ~/.cursor/skills/
  └── Codex        → ~/.codex/skills/

Project Workspace (项目本地技能目录)
  └── my-project/.claude/skills/

Linked Workspace (自定义目录)
  └── /任意路径/作为技能根目录
```

## 功能详解

### 1. 统一技能库（Library）

- 从多种来源安装技能：本地文件夹、Git 仓库、压缩包、skills.sh 市场
- 所有技能汇入中央仓库，统一管理
- 支持更新追踪：Git 类技能检查上游更新，本地技能重新导入

### 2. 市场 + AI 搜索（Marketplace）

- 集成 [skills.sh](https://skills.sh) 市场，浏览热门技能
- 关键词搜索
- 支持 SkillsMP AI 搜索（需 API Key）

### 3. 预设系统（Presets）

- 将技能分组为命名预设（如 "Web Dev"、"Data Science"）
- 在任意 workspace 中点击预设药丸按钮，一键激活/停用所有技能
- 激活是一次性复制，非实时同步
- 侧边栏列出所有预设，快速访问

### 4. 三层 Workspace 模型

| 类型              | 说明                                 | 示例                          |
| ----------------- | ------------------------------------ | ----------------------------- |
| Global Workspace  | 管理每个 agent 的全局技能目录        | `~/.claude/skills/`           |
| Project Workspace | 管理项目本地技能，支持双向同步       | `my-project/.claude/skills/`  |
| Linked Workspace  | 指向任意目录作为技能根，独立管理     | `/custom/path/`               |

- Global Workspace 的关键特性：列出目录中**所有**技能（包括非 Skills Manager 安装的），可"认领"已有技能
- Project Workspace 支持与中央库对比、双向同步、嵌套技能目录、per-agent 分配

### 5. 多工具同步（Multi-tool Sync）

- 每个技能卡片显示 agent 图标徽章
- 点击徽章即可为该 agent 安装/移除技能
- 徽章实时反映同步状态
- 支持 symlink 和 copy 两种同步模式

### 6. 统一添加面板（Add Skills Sheet）

- 在任意 workspace 中点击 `+ Add Skills` 打开
- 搜索中央库，切换目标 agent（始终可见的 chip），批量添加

### 7. 批量操作

- 多选技能 → 批量启用/禁用、导出、删除
- Project Workspace 支持项目本地技能的批量操作

### 8. 标签系统（Tags）

- 为技能打标签，分组管理
- 按来源或标签过滤
- "Untagged" 快速筛选未分类技能

### 9. Git 备份/恢复

- 将 `skills/` 目录纳入 Git 版本控制
- 支持 SSH / HTTPS（PAT）认证
- 自动处理 pull → commit → push
- 每次同步创建快照版本标签
- Version History 查看时间线，恢复任意快照

### 10. CLI

- 与桌面端共享 Rust 核心，操作同一个 SQLite 数据库
- 完整的命令组：`repo`、`tools`、`skills`、`presets`、`git`
- 支持 `--json` 输出（脚本/agent 友好）
- 支持 `--skills-root` 指定外部技能仓库
- 可通过 `cargo install` 安装到 PATH

### 11. 其他

- **Custom Tools** — 自定义添加 agent/工具，指定技能目录
- **Activity Log** — 安装/移除/更新/同步操作本地记录
- **Export Logs** — 打包日志为 zip，方便 issue 报告
- **灵活设置** — 仓库路径、同步模式、主题、文字大小、语言、托盘行为、代理、Git 远程、更新检查、agent 排序

## UX 设计亮点

1. **技能卡片徽章** — 每张卡片直接显示已启用的 agent 图标，点击切换，状态一目了然
2. **Preset 药丸按钮** — 在 workspace 页面顶部横向排列，点击即激活，✓ 表示已激活，数字角标表示部分安装
3. **统一选择器** — `+ Add Skills` 面板内 agent chip 始终可见（select-all / clear），无需跳转
4. **All Agents 概览** — Global Workspace 支持"所有 agent"视图，一次管理全部
5. **内嵌 Help** — Settings 中的 Help 按钮镜像完整产品流程，相当于应用内文档

## 工程化

- **GitHub Issue 模板** — bug report + feature request
- **CI/CD** — prepare-release + release 自动化工作流
- **双语文档** — 中英文 README + CHANGELOG
- **CLI `--json` 输出** — 机器可读，方便自动化调用

## 与我们项目的对比

| 维度           | xingkongliang/skills-manager        | 我们的项目 (su/skills manager)    |
| -------------- | ------------------------------------ | --------------------------------- |
| 技术栈         | Tauri 2 + Rust + React 19            | Python + Flet                     |
| 支持工具数     | 15+（含自定义）                      | 4（Claude/Gemini/OpenAI/MCP）     |
| Marketplace    | ✅ skills.sh 集成 + AI 搜索          | ❌ 无                             |
| Preset 系统    | ✅ 命名预设，一键应用                | ❌ 无                             |
| Workspace 模型 | 三层（Global/Project/Linked）        | 二层（Global/Project）            |
| Git 备份       | ✅ 版本控制 + 多机同步 + 快照恢复    | ❌ 无                             |
| CLI            | ✅ 与桌面端共享 Rust 核心            | ✅ 独立实现                       |
| 批量操作       | ✅ 全面                              | 部分                              |
| 标签系统       | ✅                                   | ❌ 无                             |
| MCP 管理       | ❌                                   | ✅ **我们的优势**                 |
| 技能推荐       | ❌                                   | ✅ **我们的优势**                 |
| 技能编辑器     | ❌                                   | ✅ **我们的优势**                 |
| 技能打包       | ❌                                   | ✅ **我们的优势**                 |

## 可借鉴的设计

### 高优先级

1. **Preset 系统** — 用户创建命名技能组，一键应用到不同场景。这是提升日常使用效率的关键功能，实现复杂度适中
2. **Marketplace 集成** — 接入社区技能市场（或自建），让用户浏览和安装现成技能。降低使用门槛，扩大用户群
3. **技能卡片徽章交互** — 在技能卡片上直接显示已启用的 agent 徽章，点击切换状态。UX 上非常直观

### 中优先级

4. **Git 备份/恢复** — 给技能库加上版本控制，支持多机同步。对多设备用户是刚需
5. **统一添加面板** — 在 workspace 内直接搜索库并批量添加，agent chip 切换始终可见
6. **`--json` CLI 输出** — 让 CLI 支持机器可读输出，方便脚本和 agent 调用
7. **标签系统** — 技能分类和过滤，Untagged 快速筛选

### 低优先级

8. **Linked Workspace** — 自定义目录作为技能根，满足非标准路径需求
9. **Activity Log + Export** — 操作记录和日志导出，方便问题排查
10. **All Agents 概览** — 一次管理所有 agent 的全局技能

## 我们的差异化优势

### MCP 配置管理

xingkongliang/skills-manager 完全不涉及 MCP server 管理。我们已经实现了：
- MCP server 的添加/编辑/删除
- 环境变量管理
- 全局/项目级配置
- 从其他工具导入配置

这是**独特的功能定位**，可以作为核心卖点。

### 技能推荐

我们有推荐页面，可以根据用户已安装的技能推荐相关技能。他们没有这个功能。

### 内嵌编辑器

我们支持在应用内直接编辑技能内容（SKILL.md），他们只能预览。

### 技能打包

我们支持将技能打包为 `.skill` 文件，方便分享和分发。

## 技术栈选型思考

| 方面     | Tauri 2 + Rust                    | Python + Flet                |
| -------- | --------------------------------- | ---------------------------- |
| 性能     | ⭐⭐⭐⭐⭐ 原生级别               | ⭐⭐⭐ 良好                   |
| 包体大小 | ⭐⭐⭐⭐⭐ ~5-10MB                 | ⭐⭐ ~50-100MB（含 Python）   |
| 开发效率 | ⭐⭐⭐ 需要 Rust 知识             | ⭐⭐⭐⭐⭐ Python 生态，快速迭代 |
| 跨平台   | ⭐⭐⭐⭐⭐ Windows/macOS/Linux     | ⭐⭐⭐⭐ Windows/macOS/Linux   |
| 生态成熟 | ⭐⭐⭐⭐ 前端生态丰富              | ⭐⭐⭐ Flet 较新，社区较小    |
| 学习曲线 | ⭐⭐ Rust + 前端双重门槛          | ⭐⭐⭐⭐⭐ Python 低门槛        |

**结论**：Tauri + Rust 方案在性能和包体上有明显优势，适合长期产品化。Python + Flet 方案开发效率高、迭代快，适合原型验证和快速试错。如果项目进入成熟期，可考虑渐进式迁移到 Tauri 或其他更成熟的桌面框架。

## 总结

xingkongliang/skills-manager 是一个功能非常成熟、设计精良的竞品。它的核心优势在于：

1. **功能覆盖面广** — 从市场浏览到 Git 备份，端到端闭环
2. **UX 打磨精细** — 徽章交互、预设药丸、统一选择器等细节到位
3. **工程化完善** — CLI 双端复用、CI/CD、双语文档、Issue 模板

我们的项目在 **MCP 管理**、**技能推荐**、**内嵌编辑器** 上有差异化优势。建议：

- **短期**：借鉴 Preset 系统和技能卡片徽章交互
- **中期**：接入 Marketplace + 添加 Git 备份
- **长期**：评估技术栈迁移（如 Tauri）的可行性

---

## 附录：Cursor Design 落地记录

> 实施日期：2026-06-09

已将 Cursor Design 设计规范落地到项目代码中。核心变更：

### 新增文件

- `desktop/theme.py` — 设计 Token 中心，定义所有颜色、字体、间距、圆角常量

### 设计 Token 映射

| Token | 值 | 用途 |
| ----- | --- | ---- |
| `canvas` | `#f7f7f4` | 暖羊皮纸主背景（非纯白） |
| `primary` | `#26251e` | 深咖啡墨色（文字/主色） |
| `accent` | `#f54e00` | 焦橙（CTA、badge、高信号交互） |
| `card` | `#f0efeb` | 卡片背景（无阴影，靠色差分层） |
| `card_hover` | `#ebeae5` | 卡片悬浮态 |
| `border_01` | `rgba(38,37,30,0.025)` | 最轻边框 |
| `border_02` | `rgba(38,37,30,0.1)` | 标准边框 |
| `success` | `#1f8a65` | 成功状态 |
| `error` | `#cf2d56` | 错误状态 |
| `warning` | `#d29922` | 警告状态 |

### 关键设计原则

1. **无阴影卡片** — 卡片不使用 `box-shadow`，靠 `#f7f7f4` 背景与 `#f0efeb` 卡片的色差分层
2. **焦橙仅用于 CTA** — `#f54e00` 只用于按钮、badge、进度条等高信号交互元素
3. **暖色调贯穿** — 不使用纯白 `#fff`、纯黑 `#000`，所有表面都带暖色调
4. **极淡边框** — 边框透明度 2.5%~10%，几乎不可见但提供结构感

### 涉及文件（12 个）

```
desktop/theme.py              ← 新建
desktop/app.py                ← 主题配置 + 侧边栏
desktop/components.py         ← 卡片、列表项、空状态、标签云
desktop/dialogs.py            ← 安装/卸载/更新对话框
desktop/pages/browse.py       ← 浏览页
desktop/pages/detail.py       ← 详情页
desktop/pages/editor.py       ← 编辑器页
desktop/pages/export.py       ← 导出页
desktop/pages/import_page.py  ← 导入页
desktop/pages/mcp.py          ← MCP 配置页
desktop/pages/recommend.py    ← 最近活动页
desktop/pages/settings.py     ← 设置页（自动继承主题）
```
