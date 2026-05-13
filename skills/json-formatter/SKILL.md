---
name: json-formatter
version: "1.0.0"
description: JSON 格式化、压缩与校验
summary: |
  对 JSON 字符串进行格式化（美化）、压缩（去除空白）和语法校验。
  支持自定义缩进和排序。
type: tool
tags: [json, formatting, validation]
category: code
author: skills-manager
license: MIT
---

## 功能

对 JSON 字符串进行格式化、压缩和校验。支持自定义缩进空格数和键排序。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| input | string | ✅ | 待处理的 JSON 字符串 |
| action | string | ✅ | 操作：format / minify / validate |
| indent | integer | ❌ | 缩进空格数，默认 2，仅 format 有效 |
| sort_keys | boolean | ❌ | 是否按键名排序，默认 false |

## 返回

| 字段 | 类型 | 说明 |
|---|---|---|
| result | string | 处理结果（format/minify）或空字符串（validate） |
| valid | boolean | JSON 是否合法 |
| error | string | 错误信息（仅 valid=false 时） |

## 示例

**输入**：
```json
{"input": "{\"name\":\"test\",\"value\":42}", "action": "format", "indent": 2}
```

**输出**：
```json
{"result": "{\n  \"name\": \"test\",\n  \"value\": 42\n}", "valid": true, "error": ""}
```

## 适用场景

- API 响应数据格式化
- 配置文件美化
- JSON 语法快速校验

## 不适用

- JSON Schema 校验
- JSON 转 YAML/TOML 等格式转换
