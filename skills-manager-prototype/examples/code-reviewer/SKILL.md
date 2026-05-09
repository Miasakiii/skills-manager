---
name: code-reviewer
version: "1.0.0"
description: 多语言代码审查，检测 bug、性能和安全问题
summary: |
  对代码片段进行审查，检测潜在的 bug、性能瓶颈和安全漏洞。
  支持 Python / JavaScript / TypeScript / Go / Rust 五种语言。
  输出结构化的审查报告，包含问题位置、严重级别和修复建议。
skill_type: component
intent: 对代码进行审查，检测 bug、性能和安全问题
type: tool
tags: [review, security, debugging]
category: code
author: skills-manager
license: MIT
---

## 功能

对代码片段进行审查，检测潜在的 bug、性能瓶颈和安全漏洞。输出结构化报告。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| code | string | ✅ | 待审查的代码片段 |
| language | string | ✅ | 代码语言：python / javascript / typescript / go / rust |
| focus | string | ❌ | 审查重点：bug / performance / security / all，默认 all |
| severity | string | ❌ | 最低严重级别：info / warning / error，默认 warning |

## 返回

| 字段 | 类型 | 说明 |
|---|---|---|
| issues | array | 问题列表 |
| summary | string | 审查摘要 |
| score | number | 代码质量评分 0-100 |

## 示例

**输入**：
```json
{"code": "def add(a, b): return a + b", "language": "python", "focus": "all"}
```

**输出**：
```json
{"issues": [], "summary": "No issues found. Clean and simple function.", "score": 100}
```

## 适用场景

- PR 代码审查辅助
- 代码质量检查
- 安全漏洞扫描

## 不适用

- 大型项目整体架构审查
- 代码风格检查（使用 linter）
