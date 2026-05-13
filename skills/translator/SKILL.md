---
name: translator
version: "1.0.0"
description: 多语言翻译，支持 7 种语言
summary: |
  将文本翻译到 7 种目标语言，自动检测源语言。
  支持 formal / casual / technical 三种翻译风格。
  需要配置翻译 API Key（支持 Google / DeepL / 百度）。
skill_type: component
intent: 将文本翻译到指定目标语言，保持术语一致性
type: tool
tags: [translation, i18n]
category: language
author: skills-manager
license: MIT
---

## 功能

将文本翻译到目标语言，自动检测源语言并保持术语一致性。

## 参数

| 参数 | 类型 | 必需 | 说明 |
|---|---|---|---|
| text | string | ✅ | 待翻译文本，最大 10000 字符 |
| target_lang | string | ✅ | 目标语言：zh / en / ja / ko / fr / de / es |
| style | string | ❌ | 风格：formal / casual / technical，默认 formal |

## 返回

| 字段 | 类型 | 说明 |
|---|---|---|
| translated_text | string | 翻译结果 |
| confidence | number | 置信度 0-1 |
| detected_lang | string | 检测到的源语言 |

## 示例

**输入**：
```json
{"text": "Hello world", "target_lang": "zh"}
```

**输出**：
```json
{"translated_text": "你好世界", "confidence": 0.95, "detected_lang": "en"}
```

## 适用场景

- 翻译用户反馈或评论
- 多语言内容本地化

## 不适用

- 实时口语翻译（延迟较高）
- 文学翻译（缺乏文学润色能力）
