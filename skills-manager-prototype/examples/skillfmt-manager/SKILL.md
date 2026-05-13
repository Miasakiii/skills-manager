---
name: skillfmt-manager
version: "1.0.0"
description: skillfmt Skills 管理助手
summary: |
  帮助用户通过自然语言管理 skillfmt 中的 Skills。
  支持列出、搜索、安装、卸载、导出、升级和回滚 Skills。
skill_type: interactive
intent: 让用户可以通过自然语言管理 skillfmt 中的 Skills，无需记忆 CLI 命令
tags: [skillfmt, management, automation]
category: tooling
author: skillfmt
license: MIT
---

## 功能

通过自然语言管理 skillfmt 的 Skills 生命周期：

- 查看已安装 Skills 列表
- 搜索特定 Skill
- 安装新 Skill（本地路径 / URL / GitHub）
- 卸载不再需要的 Skill
- 导出 Skill 为不同平台格式
- 升级 Skill 到新版本
- 回滚 Skill 到旧版本
- 打包 Skill 为 .skill 文件
- 检查 skillfmt 健康状态

## 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| action | string | ✅ | 操作：list / search / install / uninstall / export / upgrade / rollback / pack / doctor |
| target | string | ❌ | Skill 名称或路径（根据 action 需要） |
| format | string | ❌ | 导出格式：openai / claude / gemini / mcp / schema |
| source | string | ❌ | 安装/升级来源（路径或 URL） |
| query | string | ❌ | 搜索关键词 |
| force | boolean | ❌ | 是否强制覆盖（安装时） |

## 返回

| 字段 | 类型 | 说明 |
|------|------|------|
| result | string | 操作结果摘要 |
| data | object | 详细数据（列表/详情等） |
| success | boolean | 是否成功 |

## 示例

**列出所有 skills**：
```json
{"action": "list"}
```

**搜索 skills**：
```json
{"action": "search", "query": "json"}
```

**安装 skill**：
```json
{"action": "install", "source": "https://github.com/user/my-skill"}
```

**导出 skill**：
```json
{"action": "export", "target": "json-formatter", "format": "claude"}
```

**卸载 skill**：
```json
{"action": "uninstall", "target": "json-formatter"}
```

## 适用场景

- 通过对话界面管理 Skills
- 批量导出多个 Skills
- 快速安装社区分享的 Skills
- 自动化 Skills 维护流程

## 不适用

- 直接编辑 SKILL.md 文件内容（请使用编辑器）
- 管理 skillfmt 系统配置（请使用 CLI）
