# Changelog

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
