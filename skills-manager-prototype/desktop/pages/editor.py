"""新建/编辑 Skill 页。"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from skills_manager.adapters import get_adapter, list_formats
from skills_manager.parser import parse_skill_md
from skills_manager.ir import SkillIR
from skills_manager.validator import validate_skill_md

SKILL_TEMPLATE = """---
name: {name}
version: "{version}"
description: {description}
tags: [{tags}]
category: {category}
---

## 功能

{description}

## 参数

| 参数 | 类型 | 必需 | 说明 |
| --- | --- | --- | --- |
| input | string | ✅ | 输入内容 |

## 返回

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| result | string | 处理结果 |

## 示例

输入：
```json
{{"input": "example"}}
```

输出：
```json
{{"result": "output"}}
```
"""

CATEGORIES = ["language", "code", "data", "research", "writing", "automation", "agent", "misc"]


def build_editor_page(app) -> ft.Control:
    name = getattr(app, "_new_skill_name", "")
    version = getattr(app, "_new_skill_version", "1.0.0")
    description = getattr(app, "_new_skill_description", "")
    category = getattr(app, "_new_skill_category", "misc")
    tags = getattr(app, "_new_skill_tags", "")
    skill_type = getattr(app, "_new_skill_type", "component")
    intent = getattr(app, "_new_skill_intent", "")

    preview_format = getattr(app, "_preview_format", "markdown")
    generated_content = getattr(app, "_generated_content", "")

    # 预览区域
    preview_text = ft.Text(
        generated_content or "填写表单后，预览会自动更新",
        font_family="monospace",
        size=12,
        selectable=True,
    )
    preview_container = ft.Container(
        content=preview_text,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border_radius=8,
        padding=16,
        expand=True,
    )

    # 校验结果区域
    validation_column = ft.Column(spacing=4)
    validation_container = ft.Container(
        content=validation_column,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border_radius=8,
        padding=12,
    )

    # 格式选择
    format_dropdown = ft.Dropdown(
        label="预览格式",
        options=[
            ft.DropdownOption("markdown", text="SKILL.md"),
            ft.DropdownOption("openai", text="OpenAI"),
            ft.DropdownOption("claude", text="Claude"),
            ft.DropdownOption("gemini", text="Gemini"),
            ft.DropdownOption("mcp", text="MCP"),
            ft.DropdownOption("schema", text="JSON Schema"),
        ],
        value=preview_format,
        width=150,
        on_select=lambda e: on_format_change(e.control.value),
    )

    def generate_content():
        """生成 SKILL.md 内容。"""
        n = name.strip()
        if not n:
            return ""
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        skill_type_line = f"skill_type: {skill_type}" if skill_type else ""
        intent_line = f"intent: {intent}" if intent.strip() else ""

        lines = [
            "---",
            f"name: {n}",
            f'version: "{version.strip() or "1.0.0"}"',
            f"description: {description.strip() or n}",
        ]
        if skill_type_line:
            lines.append(skill_type_line)
        if intent_line:
            lines.append(intent_line)
        lines.extend([
            f'tags: [{", ".join(tag_list)}]',
            f"category: {category}",
            "---",
            "",
            "## 功能",
            "",
            description.strip() or n,
            "",
            "## 参数",
            "",
            "| 参数 | 类型 | 必需 | 说明 |",
            "| ---- | ---- | ---- | ---- |",
            "| input | string | ✅ | 输入内容 |",
            "",
            "## 返回",
            "",
            "| 字段 | 类型 | 说明 |",
            "| ---- | ---- | ---- |",
            "| result | string | 处理结果 |",
            "",
            "## 示例",
            "",
            "输入：",
            '```json',
            '{"input": "example"}',
            "```",
            "",
            "输出：",
            '```json',
            '{"result": "output"}',
            "```",
        ])
        return "\n".join(lines)

    def update_preview():
        """更新预览内容。"""
        content = generate_content()
        app._generated_content = content

        if preview_format == "markdown":
            preview_text.value = content or "填写表单后，预览会自动更新"
        else:
            # 导出格式预览
            if content:
                try:
                    # 解析 SKILL.md 生成 IR
                    ir = parse_skill_md_string(content)
                    adapter = get_adapter(preview_format)
                    preview_text.value = adapter.export(ir)
                except Exception as e:
                    preview_text.value = f"导出预览错误: {e}"
            else:
                preview_text.value = "请先填写表单"

        # 实时校验
        validation_column.controls.clear()
        if content:
            vr = validate_skill_md(content)
            if vr.errors:
                for err in vr.errors:
                    validation_column.controls.append(
                        ft.Row([
                            ft.Icon(ft.Icons.ERROR_OUTLINE, size=14, color=ft.Colors.ERROR),
                            ft.Text(err, size=12, color=ft.Colors.ERROR),
                        ], spacing=4)
                    )
            if vr.warnings:
                for warn in vr.warnings:
                    validation_column.controls.append(
                        ft.Row([
                            ft.Icon(ft.Icons.WARNING_AMBER, size=14, color=ft.Colors.ORANGE),
                            ft.Text(warn, size=12, color=ft.Colors.ORANGE),
                        ], spacing=4)
                    )
            if not vr.errors and not vr.warnings:
                validation_column.controls.append(
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=14, color=ft.Colors.GREEN),
                        ft.Text("格式校验通过", size=12, color=ft.Colors.GREEN),
                    ], spacing=4)
                )

        app._update_ui()

    def on_field_change(field_name, value):
        """字段变化时更新预览。"""
        setattr(app, f"_new_skill_{field_name}", value)
        update_preview()

    def on_format_change(value):
        """切换预览格式。"""
        app._preview_format = value
        preview_format = value
        update_preview()

    def on_generate(_):
        """生成并保存。"""
        n = name.strip()
        if not n:
            app.show_snack("请输入 Skill 名称", error=True)
            return
        update_preview()
        app.show_snack("骨架已生成")

    async def save_skill():
        content = app._generated_content
        n = name.strip()
        if not content:
            app.show_snack("请先生成 Skill 骨架", error=True)
            return
        # 保存前校验
        vr = validate_skill_md(content)
        if vr.errors:
            app.show_snack(f"格式有误，请先修复: {vr.errors[0]}", error=True)
            return
        save_dir = await ft.FilePicker().get_directory_path()
        if not save_dir:
            return
        try:
            skill_dir = Path(save_dir) / n
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
            app.store.install(skill_dir, force=True)
            app._refresh_skills()
            app.show_snack(f"Skill '{n}' 已创建并安装")
            app.navigate("browse")
        except Exception as e:
            app.show_snack(f"保存失败: {e}", error=True)

    def save_skill_wrapper():
        import asyncio
        asyncio.ensure_future(save_skill())

    # 初始预览
    if generated_content:
        update_preview()

    return ft.Row(
        spacing=16,
        expand=True,
        controls=[
            # 左侧：表单
            ft.Container(
                width=400,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=12,
                    controls=[
                        ft.Text("新建 Skill", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text("填写基本信息，自动生成 SKILL.md", size=13),
                        ft.Divider(),
                        ft.TextField(
                            label="名称",
                            hint_text="my-skill",
                            value=name,
                            on_change=lambda e: on_field_change("name", e.control.value),
                        ),
                        ft.TextField(
                            label="版本",
                            hint_text="1.0.0",
                            value=version,
                            on_change=lambda e: on_field_change("version", e.control.value),
                        ),
                        ft.TextField(
                            label="描述",
                            hint_text="简要描述此 Skill 的功能",
                            value=description,
                            on_change=lambda e: on_field_change("description", e.control.value),
                            multiline=True,
                            min_lines=2,
                        ),
                        ft.Dropdown(
                            label="语义类型",
                            options=[
                                ft.DropdownOption("component", text="模板/制品"),
                                ft.DropdownOption("interactive", text="引导式对话"),
                                ft.DropdownOption("workflow", text="端到端流程"),
                            ],
                            value=skill_type,
                            on_select=lambda e: on_field_change("skill_type", e.control.value),
                        ),
                        ft.TextField(
                            label="意图说明",
                            hint_text="这个 Skill 要解决什么问题",
                            value=intent,
                            on_change=lambda e: on_field_change("intent", e.control.value),
                        ),
                        ft.Dropdown(
                            label="分类",
                            options=[ft.DropdownOption(c) for c in CATEGORIES],
                            value=category,
                            on_select=lambda e: on_field_change("category", e.control.value),
                        ),
                        ft.TextField(
                            label="标签",
                            hint_text="translation, i18n（逗号分隔）",
                            value=tags,
                            on_change=lambda e: on_field_change("tags", e.control.value),
                        ),
                        ft.Divider(),
                        ft.Row([
                            ft.FilledButton("生成骨架", icon=ft.Icons.AUTO_AWESOME, on_click=on_generate),
                            ft.FilledButton("保存 Skill", icon=ft.Icons.SAVE, on_click=lambda _: save_skill_wrapper()),
                        ]),
                    ],
                ),
            ),
            # 右侧：预览 + 校验
            ft.Container(
                expand=True,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row([
                            ft.Text("预览", size=18, weight=ft.FontWeight.BOLD),
                            format_dropdown,
                        ]),
                        preview_container,
                        ft.Text("格式校验", size=14, weight=ft.FontWeight.BOLD),
                        validation_container,
                    ],
                ),
            ),
        ],
    )


def parse_skill_md_string(content: str) -> SkillIR:
    """从字符串解析 SKILL.md（不需要文件）。"""
    import re
    import yaml

    # 提取 frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        raise ValueError("No frontmatter found")

    fm = yaml.safe_load(match.group(1))
    body = content[match.end():]

    # 解析参数表格
    params = []
    param_match = re.search(r'## 参数\s*\n(.*?)(?=\n## |\Z)', body, re.DOTALL)
    if param_match:
        table_text = param_match.group(1)
        for line in table_text.strip().split('\n'):
            if '|' in line and '---' not in line and '参数' not in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 4:
                    params.append({
                        'name': parts[0],
                        'type': parts[1],
                        'required': parts[2] in ('✅', '是', 'yes', 'true'),
                        'description': parts[3],
                    })

    return SkillIR(
        name=fm.get('name', ''),
        version=str(fm.get('version', '1.0.0')),
        description=fm.get('description', ''),
        summary=fm.get('summary', ''),
        type=fm.get('type', ''),
        skill_type=fm.get('skill_type', ''),
        intent=fm.get('intent', ''),
        tags=fm.get('tags', []),
        category=fm.get('category', ''),
        parameters=params,
    )
