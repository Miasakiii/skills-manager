"""新建/编辑 Skill 页。"""

from __future__ import annotations

from pathlib import Path

import flet as ft

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

    generated_content = getattr(app, "_generated_content", "")
    generated_name = getattr(app, "_generated_name", "")

    preview_text = ft.Text(generated_content, font_family="monospace", size=12)
    preview_container = ft.Container(content=preview_text, bgcolor=ft.Colors.SURFACE_CONTAINER, border_radius=8, padding=16)
    save_btn = ft.FilledButton("保存 Skill", icon=ft.Icons.SAVE, on_click=lambda _: save_skill_wrapper())

    def on_generate(_):
        n = name.strip()
        if not n:
            app.show_snack("请输入 Skill 名称", error=True)
            return
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        content = SKILL_TEMPLATE.format(
            name=n, version=version.strip() or "1.0.0",
            description=description.strip() or n, tags=", ".join(tag_list),
            category=category,
        )
        app._generated_content = content
        app._generated_name = n
        preview_text.value = content
        app._update_ui()

    async def save_skill():
        content = getattr(app, "_generated_content", "")
        n = getattr(app, "_generated_name", "")
        if not content:
            app.show_snack("请先生成 Skill 骨架", error=True)
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

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            ft.Text("新建 Skill", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("填写基本信息，生成 SKILL.md 骨架", size=13),
            ft.Divider(),
            ft.TextField(label="名称", hint_text="my-skill", value=name,
                         on_change=lambda e: setattr(app, "_new_skill_name", e.control.value)),
            ft.TextField(label="版本", hint_text="1.0.0", value=version,
                         on_change=lambda e: setattr(app, "_new_skill_version", e.control.value)),
            ft.TextField(label="描述", hint_text="简要描述此 Skill 的功能", value=description,
                         on_change=lambda e: setattr(app, "_new_skill_description", e.control.value),
                         multiline=True, min_lines=2),
            ft.Row([
                ft.Dropdown(
                    label="分类",
                    options=[ft.DropdownOption(c) for c in CATEGORIES],
                    value=category,
                    width=200,
                    on_select=lambda e: setattr(app, "_new_skill_category", e.control.value),
                ),
                ft.TextField(label="标签", hint_text="translation, i18n（逗号分隔）", value=tags, expand=True,
                             on_change=lambda e: setattr(app, "_new_skill_tags", e.control.value)),
            ]),
            ft.Row([ft.FilledButton("生成骨架", icon=ft.Icons.AUTO_AWESOME, on_click=on_generate)]),
            ft.Divider(),
            preview_container,
            ft.Row([save_btn]),
        ],
    )
