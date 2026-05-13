# Skills Manager (skillfmt)

## 项目概述

Skills Manager 是一个 AI Skill 格式转换工具。用户编写一次 SKILL.md 定义，即可一键导出为 OpenAI Function Calling、Claude Tool Use、Gemini Function Declaration、MCP Server、JSON Schema 等主流平台格式。

- **PyPI 包名**: `skillfmt`
- **CLI 命令**: `skillfmt`
- **版本**: v0.1.4

## 技术栈

- **Python 3.12+** — 核心引擎
- **Flet 0.84** — 桌面 GUI
- **Typer** — CLI 框架
- **pytest** — 测试
- **ruff** — 代码格式与检查
- **GitHub Actions** — CI/CD（三平台构建 + PyPI 发布）

## 目录结构

```
skills-manager/
├── src/skills_manager/        # 核心引擎
│   ├── ir.py                  # Skill 中间表示（SkillIR dataclass）
│   ├── parser.py              # SKILL.md 解析器（frontmatter + markdown body）
│   ├── validator.py           # 格式验证器
│   ├── store/                 # 本地存储管理（mixin 子包）
│   │   ├── core.py            # 索引、查询、搜索
│   │   ├── installer.py       # 安装/升级/回滚
│   │   ├── scanner.py         # 目录扫描与自动发现
│   │   ├── category.py        # 自动分类
│   │   └── history.py         # 使用/导出历史、收藏
│   ├── adapters/              # 格式适配器
│   │   ├── openai.py          # OpenAI Function Calling
│   │   ├── claude.py          # Claude Tool Use
│   │   ├── gemini.py          # Gemini Function Declaration
│   │   ├── mcp.py             # MCP Python Server
│   │   └── json_schema.py     # JSON Schema
│   ├── server/                # MCP Server + HTTP API
│   │   ├── mcp_server.py      # MCP Server（stdio 模式）
│   │   └── api.py             # FastAPI HTTP API
│   ├── cli.py                 # CLI 入口（Typer）
│   ├── updater.py             # 自动更新检查
│   └── security.py            # 路径穿越防护
├── desktop/                   # 桌面客户端（Flet 0.84）
│   ├── app.py                 # 主控类（App）
│   ├── components.py          # 可复用 UI 组件
│   ├── dialogs.py             # 对话框
│   └── pages/                 # 页面（browse/detail/export/editor/settings 等）
├── tests/                     # 测试（331 passed）
├── examples/                  # 示例 Skills
└── docs/                      # 用户文档
```

## 编码规范

### 错误消息

- **Store 层异常**（`StoreError`）统一使用英文，面向开发者/日志
- **CLI 输出**和**桌面端 UI 文本**使用中文，面向中文终端用户

### 类型注解

- 所有公共函数必须标注参数和返回类型
- `from __future__ import annotations` 置于每个模块顶部

### 导入顺序

1. 标准库
2. 第三方库
3. 项目内部模块（使用相对导入 `from ..components import ...`）

## 常见开发任务

### 运行测试

```bash
pytest tests/ -q
```

### 代码质量

```bash
ruff format .
ruff check .
```

### 启动桌面应用

```bash
python -m desktop
```

### 添加新适配器

1. 在 `src/skills_manager/adapters/` 创建新文件
2. 继承 `BaseAdapter`，实现 `name`、`file_extension`、`export`
3. 在 `adapters/__init__.py` 注册
4. 添加测试

### 发布流程

1. 更新 `pyproject.toml` 版本号
2. 更新 `src/skills_manager/__init__.py` 版本号
3. 更新 `README.md` 版本徽章
4. 创建 Git tag，推送到仓库
5. GitHub Actions 自动构建三平台安装包并发布到 PyPI

## 状态管理（桌面端）

`App` 类在 `__init__` 中显式声明所有状态属性，禁止通过 `setattr`/`getattr` 动态挂载新属性。各页面直接访问 `app.xxx`，不再使用 `getattr(app, "xxx", default)`。

## 注意事项

- `store/` 子包使用 mixin 模式拆分职责，最终 `Store` 类通过多重继承组合
- Flet `FilePicker` 在 `App` 级别单例创建，注册到 `page.overlay`，各页面复用 `app.file_picker`
- 桌面端页面构建函数统一接收 `app` 参数，返回 `ft.Control`
- 内部规划文档（IMPROVEMENTS.md 等）不推送到远程仓库
