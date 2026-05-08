# Skills Manager — 项目任务书

> **版本**：v3.0  
> **日期**：2026-05-08  
> **状态**：立项（Python 优先桌面客户端方向）

---

## 一、项目概述

### 1.1 一句话描述

一个跨平台桌面应用：用一种极简格式定义 AI Skill，一键导出为 OpenAI / Claude / Gemini / MCP 等主流平台的工具格式，支持可视化管理、浏览、搜索和导出。

### 1.2 解决的问题

AI Agent 生态中，工具（Tool / Skill / Plugin）的格式高度碎片化：

| 平台 | 工具定义格式 |
| --- | --- |
| OpenAI | Function Calling JSON |
| Claude | Tool Use JSON |
| Gemini | Function Declaration JSON |
| MCP | Tool JSON Schema + Server 代码 |
| LangChain | Python `@tool` 装饰器 |

**后果**：

- 同一个能力（如"翻译"），要在每个平台手写一遍定义
- 格式之间大同小异，但细微差异（字段名、大小写、嵌套结构）容易出错
- 迁移 Agent 平台时，工具定义需要逐个改写
- 没有统一的地方管理和复用已有的工具定义
- CLI 工具对非技术用户门槛高，缺乏可视化操作界面

### 1.3 核心价值（按优先级）

1. **格式转换**：一份定义 → 多平台格式。省掉重复劳动，消灭格式错误
2. **可视化管理**：桌面客户端提供直观的 Skill 浏览、搜索、编辑和导出体验
3. **本地管理**：所有 Skill 统一存储，安装、搜索、查看一条命令或一次点击搞定
4. **打包分享**：通过 `.skill` 包或 URL 分发，方便团队复用

### 1.4 非目标（明确不做）

| 不做 | 理由 |
| --- | --- |
| 远程 Registry / 插件市场 | v1 用 GitHub Releases 替代，v2 根据用户量决定 |
| 沙箱执行（Docker/WASM） | v1 信任本地执行，安全靠用户自律 |
| Skill 运行时（接收工具调用并执行） | v1 只做格式导出，不做运行时代理 |
| 完整的依赖解析 | v1 不做 Skill 间依赖 |
| Dify / Coze 等平台适配 | v2 根据需求决定 |
| 移动端适配 | 桌面优先，移动端暂不考虑 |

---

## 二、产品形态

### 2.1 桌面客户端（主要形态）

基于 **Python + Flet** 构建的跨平台桌面应用，Windows 为主力平台，兼容 macOS 和 Linux。

**核心交互**：

- 可视化 Skill 库：卡片式浏览、分类筛选、关键词搜索
- 一键导出：选中 Skill → 选择目标平台 → 复制或保存
- Skill 编辑器：内置 Markdown 编辑器，实时预览解析结果
- Profile 管理：拖拽式配置 Agent 的 Skill 组合
- 批量操作：多选导出、批量安装、批量更新

### 2.2 CLI 工具（可选子集）

保留 CLI 作为高级用户的快捷入口和自动化集成方式。

```bash
skills-manager export <name> --format openai
skills-manager list
skills-manager search <query>
```

CLI 和桌面客户端共享同一套核心引擎代码。

---

## 三、Skill 格式设计原则

**极简优先，上手 < 5 分钟。**

一个 Skill 的最小定义只需要一个文件：

```text
my-skill/
├── SKILL.md        # 唯一必需文件：元数据 + 说明 + schema
└── handler.py      # 可选：执行逻辑
```

`SKILL.md` 使用 YAML frontmatter + Markdown body：

````markdown
---
name: translator
version: "1.0.0"
description: 多语言翻译，支持 7 种语言
tags: [translation, i18n]
---

## 功能

将文本翻译到目标语言，自动检测源语言。

## 参数

| 参数 | 类型 | 必需 | 说明 |
| --- | --- | --- | --- |
| text | string | ✅ | 待翻译文本 |
| target_lang | string | ✅ | 目标语言代码：zh/en/ja/ko/fr/de/es |
| style | string | ❌ | 翻译风格：formal/casual/technical，默认 formal |

## 返回

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| translated_text | string | 翻译结果 |
| confidence | number | 置信度 0-1 |
| detected_lang | string | 检测到的源语言 |

## 示例

输入：
```json
{"text": "Hello world", "target_lang": "zh"}
```

输出：
```json
{"translated_text": "你好世界", "confidence": 0.95, "detected_lang": "en"}
```
````

**设计决策**：

- 用 Markdown 而不是 YAML 嵌套 JSON Schema 来描述参数——人写得快、读得懂
- 工具自动从 Markdown 表格解析出 JSON Schema，不需要用户手写 Schema
- 扩展字段（executor、config、security 等）全部可选，用到时再加

---

## 四、功能范围

### 4.1 核心功能（必须）

#### 格式引擎

| 功能 | 说明 |
| --- | --- |
| SKILL.md 解析 | YAML frontmatter + Markdown body → IR（中间表示） |
| OpenAI 导出 | Function Calling JSON 格式 |
| Claude 导出 | Tool Use JSON 格式 |
| Gemini 导出 | Function Declaration JSON 格式 |
| MCP 导出 | 可运行的 MCP Server Python 脚本 |
| JSON Schema 导出 | 纯 JSON Schema 格式 |
| 批量导出 | 一次导出多个 Skill 到指定目录 |

#### 桌面客户端

| 功能 | 说明 |
| --- | --- |
| Skill 浏览 | 卡片式列表，按分类分组展示，显示名称、版本、摘要 |
| 分类筛选 | 一级分类（语言处理/编程开发/数据分析等）快速筛选 |
| 关键词搜索 | 实时搜索 Skill 名称、描述、标签 |
| Skill 详情 | 点击查看完整信息：参数表、示例、适用场景 |
| 导出面板 | 选择目标格式 → 预览导出结果 → 复制/保存 |
| 内置编辑器 | Markdown 编辑器，实时预览解析结果和 IR |
| 新建 Skill | 引导式创建 SKILL.md，自动生成骨架 |
| 安装管理 | 从本地目录 / .skill 包安装，拖拽安装 |
| 卸载 | 一键卸载已安装 Skill |

#### 本地存储

| 功能 | 说明 |
| --- | --- |
| 安装 | 从本地目录 / .skill 包安装 Skill |
| 卸载 | 删除已安装 Skill |
| 列表 | 显示所有已安装 Skill |
| 详情 | 查看 Skill 完整信息 |
| 搜索 | 按关键词搜索 |
| 打包 | 将 Skill 目录打包为 .skill 文件 |

### 4.2 重要功能（应该有）

| 功能 | 说明 |
| --- | --- |
| Profile 管理 | 可视化创建 Agent Profile，拖拽添加 Skill，一键导出 |
| 场景推荐 | 输入场景描述，推荐最合适的 Skill |
| 分类浏览 | 按分类树浏览，支持二级标签筛选 |
| 从 URL 安装 | 输入 URL 或 GitHub 仓库地址，自动下载安装 |
| 更新 | 从原来源重新安装最新版 |
| 元数据补全 | 用 LLM 自动补全缺失的分类和描述 |
| Skill 配置 | 管理 Skill 的用户配置（如 API Key） |
| 主题切换 | 亮色 / 暗色主题 |
| 导出历史 | 记录导出操作，支持快速重复导出 |
| 快捷键 | 全局快捷键支持（Ctrl+E 快速导出等） |

### 4.3 后续扩展（Phase 2+）

- LangChain `@tool` Python 代码导出
- LlamaIndex `FunctionTool` 导出
- Agent Profile 一键部署到 Agent 框架
- `skills-manager publish --github` 发布到 GitHub Releases
- Skill 版本对比（diff）
- 团队协作（共享 Skill 库）
- 插件系统（自定义导出格式）

---

## 五、用户场景

### 场景 1：可视化管理 Skill 库

```text
打开桌面客户端 → 浏览已安装的 Skills（卡片列表）
→ 点击 "translator" 查看详情（参数表、示例）
→ 点击 "导出" → 选择 "OpenAI" → 预览 JSON → 复制到剪贴板
→ 粘贴到 Agent 代码中
```

### 场景 2：快速创建新 Skill

```text
点击 "新建 Skill" → 填写名称、描述
→ 在内置编辑器中编写 SKILL.md
→ 右侧实时预览解析结果（IR）
→ 确认无误 → 保存
→ 一键导出到多个平台
```

### 场景 3：批量导出迁移

```text
选中多个 Skills（Ctrl+多选）
→ 右键 "批量导出" → 选择 "Claude" 格式
→ 选择输出目录 → 导出
→ 一次性获得所有 Skill 的 Claude 格式定义
```

### 场景 4：CLI 快速操作

```bash
# 高级用户也可以用 CLI
skills-manager export translator --format openai
skills-manager list
skills-manager search "翻译"
```

---

## 六、技术选型

### 6.1 桌面客户端

| 层面 | 选择 | 理由 |
| --- | --- | --- |
| 语言 | Python 3.11+ | 生态丰富、开发速度快、团队熟悉 |
| UI 框架 | Flet 0.84（基于 Flutter） | 现代 UI、跨平台、Python 原生、组件库质量好。原型已验证通过 |
| 后端引擎 | Python（与 CLI 共享） | 同一代码库，`import skills_manager` 即用 |
| 本地存储 | JSON 索引 + 文件存储（v1），预留 SQLite 升级路径 | 轻量零依赖，满足当前规模 |
| 打包分发 | PyInstaller / Nuitka | 单文件可执行，用户无需安装 Python |

### 6.2 核心引擎（Python）

| 层面 | 选择 | 理由 |
| --- | --- | --- |
| SKILL.md 解析 | Python（PyYAML + regex） | 迭代快、文本处理库丰富 |
| IR 数据结构 | Python dataclass | 轻量、零额外依赖、类型安全 |
| 适配器引擎 | Python ABC 类 + 注册表 | 格式转换逻辑，可扩展 |
| 本地存储 | JSON 文件索引（v1） | 轻量、标准库支持。预留 SQLite 升级接口 |
| 打包/解包 | Python tarfile/zipfile | 标准库支持 |
| CLI | Python typer + rich | 类型安全、自动补全、输出美观 |

### 6.3 为什么选 Python + Flet

| 对比项 | Python + Flet | Tauri 2（Rust） | Electron + JS |
| --- | --- | --- | --- |
| 安装包体积 | ~30-50 MB（打包后） | ~5-15 MB | ~150-200 MB |
| 开发速度 | ⚡ 快 | 🐢 慢（Rust 学习曲线） | 中等 |
| UI 质量 | Flutter 渲染，现代感强 | 原生 WebView，现代 | Chromium，现代 |
| 团队匹配 | ✅ Python 团队 | ❌ 需要 Rust 经验 | ✅ JS 团队 |
| 跨平台 | ✅ | ✅ | ✅ |
| 迭代速度 | ⚡ 快 | 🐢 编译慢 | 中等 |

**结论**：Python + Flet 是最快出产品的路径。团队是 Python 原生的，Flet 的 Flutter 渲染引擎能交付现代 UI 体验。安装包体积对桌面工具来说可以接受。**Rust 移植作为后续性能优化的可选任务。**

---

## 七、实现路线图

### Phase 1：核心引擎 + CLI（第 1-3 周）✅ 已完成

**目标**：Parser + IR + 所有适配器能跑通，CLI 可用。纯 Python。

- [x] Python 项目脚手架（pyproject.toml, src layout）
- [x] SKILL.md 解析器（YAML frontmatter + Markdown body → IR）
- [x] IR 数据结构定义（dataclass 模型）
- [x] 参数表 Markdown → JSON Schema 转换
- [x] OpenAI 适配器
- [x] Claude 适配器
- [x] Gemini 适配器
- [x] MCP 适配器（Python 脚本生成）
- [x] JSON Schema 适配器
- [x] 本地存储（JSON 索引 + 文件存储）
- [x] 安装 / 卸载 / 列表 / 搜索
- [x] 打包 / 解包（.skill 文件）
- [x] CLI 入口（typer + rich）
- [x] 单元测试 + 集成测试（62 tests, 100% pass）

> **实现说明**：IR 模型使用 Python dataclass（非 Pydantic）以保持零强依赖；CLI 框架选用 typer（非 click）以获得更好的类型提示和自动补全；当前存储使用 JSON 文件索引（非 SQLite），轻量且满足当前需求。后续可平滑升级到 SQLite + FTS5。

**交付物**：`skills-manager export my-skill --format openai` 能跑通，5 个平台格式导出正确。3 个示例 Skill 的 15 次导出（3×5 格式）全部验证通过。

### Phase 2：桌面客户端 MVP（第 4-6 周）🔄 原型已验证

**目标**：基本可用的桌面应用。Python + Flet。

> **原型验证（2026-05-08）**：Flet 0.84 原型已跑通 — 侧边栏导航、Skill 卡片网格、详情页 + 导出预览、批量导出页均可用。Flet 与核心引擎集成零摩擦（`import skills_manager` 即用）。Flutter 引擎首次需下载（~40MB zip），后续秒开。结论：Flet 方案可行。

- [x] Flet 项目脚手架（主应用结构）
- [x] 主界面布局（侧边栏导航 + 内容区）— 原型完成
- [x] Skill 浏览页（卡片列表）— 原型完成
- [ ] 搜索功能（实时关键词搜索）
- [x] Skill 详情页（参数表、导出预览）— 原型完成
- [x] 导出面板（格式选择 → 预览 → 复制）— 原型完成
- [ ] 批量导出（多选 → 批量导出文件）
- [ ] 新建 Skill 引导（模板生成 SKILL.md 骨架）
- [ ] 安装管理（本地目录 / .skill 包安装）
- [x] 暗色 / 亮色主题切换 — Flet 内置支持
- [ ] 基础错误处理和 Toast 提示

**交付物**：可安装运行的桌面应用，核心流程（浏览 → 导出）跑通。

### Phase 3：编辑器与增强（第 7-9 周）

**目标**：内置编辑器、Profile 管理、远程安装。

- [ ] 内置 Markdown 编辑器（CodeMirror via Flet WebView 或自定义组件）
- [ ] 实时解析预览（编辑 SKILL.md → 即时显示 IR）
- [ ] 语法校验（frontmatter 格式检查、参数表格式检查）
- [ ] Profile 管理界面（创建 / 编辑 / 导出）
- [ ] 拖拽式 Profile 配置
- [ ] 从 URL / GitHub 安装
- [ ] 更新功能
- [ ] 场景推荐
- [ ] 导出历史记录
- [ ] 全局快捷键
- [ ] 设置页（默认格式、主题、存储路径等）

**交付物**：功能完整的桌面应用，覆盖任务书 80% 功能。

### Phase 3.5：Rust 性能优化（第 10-12 周，可选）

**目标**：将性能关键路径移植到 Rust 以提速。仅在 profiling 证明 Python 是瓶颈时执行。

- [ ] 对 Python 引擎做性能分析，定位瓶颈
- [ ] 将 SKILL.md 解析器移植到 Rust（通过 PyO3/maturin 绑定）
- [ ] 将格式适配器移植到 Rust
- [ ] Rust 核心作为 Python 扩展模块（drop-in 替换）
- [ ] 基准测试：Python vs Rust 解析器在 1000+ Skill 下的表现
- [ ] 桌面客户端透明切换到 Rust 引擎（用户无感知）
- [ ] 打包：Rust 扩展与 Python 应用一起分发

**交付物**：Rust 引擎作为可选性能升级。桌面应用从用户角度无变化。

> **关键原则**：Rust 优化是**可选的、性能驱动的**。如果 Python 性能已经够用（典型操作 < 100ms），完全可以跳过这个阶段。Python 代码库始终是 source of truth。

### Phase 4：打磨与发布（第 13-15 周）

**目标**：可发布。

- [ ] 完善文档和用户指南
- [ ] 编写 5+ 示例 Skill
- [ ] Windows 安装包（.exe via PyInstaller）
- [ ] macOS 安装包（.dmg）
- [ ] Linux 安装包（.deb / .AppImage）
- [ ] 自动更新机制
- [ ] 错误上报和遥测（可选）
- [ ] 性能优化（大量 Skill 时的列表虚拟滚动）
- [ ] 边界情况完善
- [ ] PyPI 发布 CLI 工具（可选）

**交付物**：v1.0 正式发布。

---

## 八、成功标准

| 指标 | 目标 |
| --- | --- |
| 上手时间 | 新用户从安装到导出第一个 Skill < 5 分钟 |
| SKILL.md 编写时间 | 最简 Skill < 5 分钟 |
| 导出格式正确性 | 导出结果可直接粘贴到目标平台使用，无需手动修改 |
| 安装包体积 | Windows 安装包 < 50 MB |
| 启动速度 | 冷启动 < 2 秒 |
| 功能覆盖 | Phase 3 结束时覆盖功能范围 80% |

---

## 九、风险与对策

| 风险 | 等级 | 对策 |
| --- | --- | --- |
| Flet 生态成熟度 | 🟢 已验证 | Flet 0.84 原型跑通，Flutter 渲染正常。降级方案 PyQt 保留 |
| 国内网络下载 Flutter 引擎 | 🟡 需注意 | Flet 首次需从 GitHub 下载 ~40MB 引擎。对策：提供离线安装包或镜像 URL（`FLET_CLIENT_URL` 环境变量） |
| Python 打包复杂度 | 🟡 待验证 | 使用 PyInstaller + Nuitka 打包；尽早测试三个平台 |
| 大量 Skill 时性能 | 🟢 已评估 | 当前 JSON 索引在 < 100 Skill 时性能无问题；超过后平滑升级 SQLite+FTS5，Store 接口不变 |
| 各平台 API 格式变动 | 🟢 已规避 | 适配器独立模块化，每个适配器一个文件，便于单独更新 |
| Markdown 解析不够精确 | 🟡 已处理 | YAML frontmatter 提供完整 schema；Markdown 表格解析 + 枚举自动检测在当前 3 个示例 Skill 上验证通过 |
| Python GIL 限制 | 🟢 无影响 | Flet 渲染进程独立；核心引擎以 I/O 为主，GIL 不是瓶颈 |

---

## 十、开放问题

1. ~~**Flet vs PyQt6**~~ → **已确认**：Flet 0.84 原型验证通过，Flutter 渲染现代感强，与 Python 核心引擎集成顺畅。降级方案 PyQt6 保留但不再优先。
2. **编辑器组件**：用 Flet 内置 TextField + Markdown 预览，还是通过 Flet WebView 嵌入 CodeMirror？需要实测 Flet Markdown 控件渲染效果后决定。
3. **CLI 分发方式**：发布到 PyPI（`pip install skills-manager`），与桌面应用共享核心引擎。已确认 typer + rich 方案效果良好。
4. **Rust 优化范围**：仅在基准测试显示 > 10 倍提速时才移植解析器 + 适配器。存储和 UI 留在 Python。当前 3 个 Skill 解析耗时 < 1ms，暂不触发。
5. **存储方案升级**：当前用 JSON 文件索引（轻量、零依赖），Skill 数量 > 100 时迁移到 SQLite + FTS5 全文搜索。迁移成本低——Store 接口不变。
6. **国内网络适配**：Flet 首次启动需从 GitHub 下载 Flutter 引擎（~40MB），国内用户需代理或手动放置。可考虑在安装文档中提供离线包下载链接。
