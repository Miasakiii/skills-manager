---
name: code-generator
version: "1.0.0"
description: 代码模板生成，支持多种语言和框架
summary: |
  根据用户需求生成代码模板，支持 React/Vue/Express/FastAPI 等主流框架。
  包含最佳实践和项目结构建议。
skill_type: component
intent: 快速生成符合最佳实践的代码模板和脚手架
type: tool
tags: [code, template, scaffolding, generator]
category: development
author: skills-manager
license: MIT
---

## 功能

根据用户需求生成代码模板：

- **组件模板**：React/Vue 组件
- **API 模板**：REST API 端点
- **测试模板**：单元测试和集成测试
- **配置模板**：项目配置文件

## 参数

| 参数 | 类型 | 必需 | 说明 |
| ---- | ---- | ---- | ---- |
| type | string | ✅ | 模型类型：component / api / test / config |
| framework | string | ✅ | 框架：react / vue / express / fastapi / flask |
| name | string | ✅ | 组件/模块名称 |
| language | string | ❌ | 语言：typescript / javascript / python，默认 typescript |
| features | array | ❌ | 附加功能：["styled-components", "testing", "storybook"] |

## 支持的模板

### React 组件

```typescript
// 生成的 React 组件模板
import React from 'react';

interface {Name}Props {
  // 定义 props
}

export const {Name}: React.FC<{Name}Props> = (props) => {
  return (
    <div>
      {/* 组件内容 */}
    </div>
  );
};

export default {Name};
```

### Vue 组件

```vue
<!-- 生成的 Vue 组件模板 -->
<template>
  <div class="{name}">
    <!-- 组件内容 -->
  </div>
</template>

<script setup lang="ts">
interface Props {
  // 定义 props
}

const props = defineProps<Props>();
</script>

<style scoped>
.{name} {
  /* 样式 */
}
</style>
```

### Express API

```typescript
// 生成的 Express 路由模板
import { Router, Request, Response } from 'express';

const router = Router();

router.get('/{name}', async (req: Request, res: Response) => {
  try {
    // 处理逻辑
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
```

### FastAPI 端点

```python
# 生成的 FastAPI 路由模板
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class {Name}Response(BaseModel):
    success: bool
    data: dict = None

@router.get("/{name}", response_model={Name}Response)
async def get_{name}():
    try:
        # 处理逻辑
        return {Name}Response(success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 示例

**输入**：

```json
{
  "type": "component",
  "framework": "react",
  "name": "UserCard",
  "language": "typescript",
  "features": ["styled-components", "testing"]
}
```

**输出**：

```json
{
  "files": [
    {
      "path": "src/components/UserCard/UserCard.tsx",
      "content": "// React 组件代码..."
    },
    {
      "path": "src/components/UserCard/UserCard.styles.ts",
      "content": "// styled-components 样式..."
    },
    {
      "path": "src/components/UserCard/UserCard.test.tsx",
      "content": "// 测试代码..."
    },
    {
      "path": "src/components/UserCard/index.ts",
      "content": "export { default } from './UserCard';"
    }
  ],
  "instructions": [
    "将文件放入 src/components/UserCard/ 目录",
    "运行 npm install styled-components @types/styled-components",
    "在需要的地方 import UserCard from '@/components/UserCard'"
  ]
}
```

## 适用场景

- 快速启动新项目
- 保持团队代码风格一致
- 学习框架最佳实践
- 减少重复性编码工作

## 不适用

- 复杂业务逻辑实现（需要人工设计）
- 性能关键代码（需要精细优化）
- 安全敏感代码（需要专业审查）
