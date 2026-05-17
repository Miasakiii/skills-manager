# Changelog

## v0.1.5 (2026-05-17)

### 新增

- **MCP 配置中心** — 一键管理 Claude Desktop / Claude Code / Cline 的 `mcpServers` JSON
  - 内置三种 profile + 自定义路径；CRUD 支持原子写入与备份
  - 桌面端 MCP 页：选择客户端 → 添加 / 启停 / 删除 / 从已安装 Skill 一键注册
  - CLI：`skillfmt mcp profiles | list | add | remove | enable | disable | install-skill`
- **使用频率分析** — 「最近活动」页升级为「最近活动 + 频率排行」
  - 30 天窗口热门 Skill 排行（使用计 1 分、导出计 2 分）
  - 导出格式分布、最近使用 / 最近导出
- **批量卸载与版本检测**
  - `skillfmt uninstall <name1> <name2> ...` 支持批量
  - `skillfmt check-updates` 表格列出可更新 Skill；`skillfmt update-all --yes` 一键更新
  - 桌面端浏览页顶部新增「检查 Skill 更新」按钮，含单项和一键更新

### 改进

- **Flet 0.85.1 升级** — Flet 1.0 Beta 系列
  - 复制按钮现已用 `page.clipboard.set()` 真实写入系统剪贴板（旧版只能弹对话框手动复制）
  - FilePicker 改为通过 `page.services` setter 注册，修复 0.85 下的 attach 报错
- 编辑器布局改为左:右 = 2:3 比例，窄窗口下不再溢出
- 「安装 Skill」对话框修复：之前 `from ..components` 错误的相对导入导致点击即崩
- CLI 运行时输出统一为英文（reclassify / serve / mcp / check-updates / update-all）

### 修复

- 测试套件不再污染用户真实的 `~/.claude/skills`、`~/.cc-switch/skills`、`~/.codex/skills`
  等目录（autouse conftest 阻断 `_AgentSync`）

### 构建 / 文档

- 335 个测试（含 53 个新增）

## v0.1.4 (2026-05-13)

### 新增

- **桌面应用** — 基于 Flet 0.84 的跨平台 GUI，支持浏览、搜索、编辑、导出 Skills
- **Server 模块** — MCP Server（stdio 模式）+ FastAPI HTTP API，让 AI Agent 通过自然语言管理 Skills
- **精选 Skills 集合** — 内置示例 Skills，一键安装体验
- **Windows 安装包** — NSIS 安装向导 (`skills-manager-setup-windows.exe`)
- **Claude Code 兼容性检查** — 自动检测 SKILL.md 是否符合 Claude Code 规范
- **Agent 目录同步** — 安装时自动用 symlink 同步到 Claude / Cline / Cursor 等工具目录

### 改进

- 桌面端字体与排版优化
- 存储层增加降级恢复机制
- CLI 支持 `check-update` 命令

### 构建

- GitHub Actions CI/CD：三平台构建（Windows / macOS / Linux）+ PyPI 自动发布
