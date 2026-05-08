---
name: sample-skill
version: "1.0.0"
description: A sample skill for testing
summary: This is a sample skill used in unit tests.
type: tool
tags: [sample, test]
category: misc
author: test
license: MIT
---

## 功能

This is a sample skill for testing the parser.

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| text | string | ✅ | Input text |
| language | string | ❌ | Target language：zh / en / ja |
| count | integer | ❌ | Number of times |

## 返回

| 字段 | 类型 | 说明 |
|---|---|---|
| result | string | Processed result |

## 示例

```json
{"text": "hello", "language": "zh"}
```

```json
{"result": "你好"}
```

## 适用场景

- Testing the parser
- Example usage

## 不适用

- Production use
