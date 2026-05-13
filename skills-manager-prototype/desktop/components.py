"""可复用 UI 组件。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import flet as ft


# ── 字体规范 ──────────────────────────────────────────────
# 建立 Material Design 3 风格层级，确保中英文混排清晰美观
FONT_DISPLAY = 28     # 大标题 / 空状态主标题
FONT_TITLE = 24       # 页面标题
FONT_HEADLINE = 18    # 区块大标题 / 详情页名称
FONT_SECTION = 15     # 区块标题 / 分类标题
FONT_SUBTITLE = 14    # 副标题 / 描述 / 统计
FONT_BODY = 13        # 正文 / 表单标签
FONT_CARD_NAME = 15   # 卡片名称（与区块标题同级）
FONT_CARD_DESC = 12   # 卡片描述
FONT_TAG = 11         # 标签 / Tag
FONT_META = 12        # 元数据（版本、分类）
FONT_SMALL = 11       # 小字（时间、角落信息）

# 全局字体栈（Windows 优先 Segoe UI + 微软雅黑，兼顾 macOS/Linux）
FONT_FAMILY_UI = "Segoe UI, Microsoft YaHei UI, PingFang SC, Noto Sans SC, system-ui, sans-serif"
FONT_FAMILY_MONO = "Cascadia Code, Consolas, monospace"


# ── 工具函数 ──────────────────────────────────────────────

def _relative_time(iso_str: str) -> str:
    """将 ISO 时间字符串转为相对时间描述（如 '3 天前'）。"""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "刚刚"
        if seconds < 3600:
            return f"{seconds // 60} 分钟前"
        if seconds < 86400:
            return f"{seconds // 3600} 小时前"
        days = seconds // 86400
        if days < 30:
            return f"{days} 天前"
        if days < 365:
            return f"{days // 30} 个月前"
        return f"{days // 365} 年前"
    except (ValueError, TypeError):
        return ""


def _source_info(source: str) -> dict:
    """根据来源返回标签、图标和颜色。"""
    if not source:
        return {"label": "本地", "icon": ft.Icons.COMPUTER, "color": ft.Colors.GREY}
    lower = source.lower()
    if "github.com" in lower:
        return {"label": "GitHub", "icon": ft.Icons.CODE, "color": ft.Colors.ON_SURFACE_VARIANT}
    if "anthropic.com" in lower:
        return {"label": "Anthropic", "icon": ft.Icons.SMART_TOY, "color": ft.Colors.BLUE}
    if "openai.com" in lower:
        return {"label": "OpenAI", "icon": ft.Icons.PSYCHOLOGY, "color": ft.Colors.GREEN}
    if "google" in lower:
        return {"label": "Google", "icon": ft.Icons.SEARCH, "color": ft.Colors.RED}
    if source.startswith(("http://", "https://")):
        return {"label": "Web", "icon": ft.Icons.LANGUAGE, "color": ft.Colors.OUTLINE}
    return {"label": "本地", "icon": ft.Icons.COMPUTER, "color": ft.Colors.GREY}


# ── 类型图标映射 ──────────────────────────────────────────

SKILL_TYPE_ICONS = {
    "component": (ft.Icons.WIDGETS_OUTLINED, "模板"),
    "interactive": (ft.Icons.CHAT_BUBBLE_OUTLINED, "对话"),
    "workflow": (ft.Icons.ACCOUNT_TREE_OUTLINED, "流程"),
    "tool": (ft.Icons.BUILD_OUTLINED, "工具"),
}

# ── 分类颜色映射 ──────────────────────────────────────────

CATEGORY_COLORS = {
    "language": ft.Colors.BLUE,
    "code": ft.Colors.GREEN,
    "data": ft.Colors.ORANGE,
    "research": ft.Colors.PURPLE,
    "writing": ft.Colors.TEAL,
    "automation": ft.Colors.RED,
    "misc": ft.Colors.GREY,
    "agent": ft.Colors.AMBER,
}


class SkillCard(ft.Container):
    """Skill 卡片组件。"""

    def __init__(
        self,
        skill_info,
        on_click,
        checkbox_mode: bool = False,
        checked: bool = False,
        on_check=None,
        compact: bool = True,
    ):
        super().__init__()
        self.skill_info = skill_info
        tag_color = CATEGORY_COLORS.get(skill_info.category, ft.Colors.GREY)

        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        self.border_radius = 16
        self.padding = 16
        self.ink = True
        self.border = ft.Border(
            left=ft.BorderSide(3, tag_color),
            top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        )
        self.elevation = 2
        self.shadow = ft.BoxShadow(
            spread_radius=0,
            blur_radius=6,
            color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
            offset=ft.Offset(0, 2),
        )
        self.animate = ft.Animation(180, ft.AnimationCurve.EASE_IN_OUT)
        self.on_click = lambda _: on_click(skill_info.name)
        self.on_hover = self._on_hover
        self._tag_color = tag_color

        # 类型图标
        skill_type = getattr(skill_info, "skill_type", "")
        type_icon, type_label = SKILL_TYPE_ICONS.get(skill_type, (ft.Icons.EXTENSION, ""))

        # 来源标识
        source = getattr(skill_info, "source", "")
        source_info = _source_info(source)

        # 复选框（批量模式）
        checkbox = None
        if checkbox_mode:
            checkbox = ft.Checkbox(
                value=checked,
                on_change=lambda e: on_check(skill_info.name, e.control.value) if on_check else None,
            )

        # 顶部行：复选框（可选）+ 类型图标 + 名称 + 来源标识
        top_left = [ft.Icon(type_icon, color=tag_color, size=20)]
        if checkbox_mode:
            top_left.insert(0, checkbox)
        top_left.append(
            ft.Text(skill_info.name, size=FONT_CARD_NAME, weight=ft.FontWeight.BOLD, color=tag_color),
        )

        top_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(top_left, spacing=6),
                ft.Container(
                    content=ft.Icon(source_info["icon"], size=16, color=source_info["color"]),
                    tooltip=source_info["label"],
                    border_radius=4,
                    padding=ft.Padding(4, 2, 4, 2),
                ),
            ],
        )

        # 描述
        desc_max_lines = 1 if compact else 3
        desc_max_len = 80 if compact else 120
        desc = ft.Text(
            (skill_info.summary or skill_info.description or "")[:desc_max_len],
            size=FONT_CARD_DESC, color=ft.Colors.ON_SURFACE_VARIANT,
            max_lines=desc_max_lines, overflow=ft.TextOverflow.ELLIPSIS,
        )

        controls = [top_row, desc]

        # 详细模式：显示标签、元数据、安装时间
        if not compact:
            # 安装时间
            installed_at = getattr(skill_info, "installed_at", "")
            time_text = _relative_time(installed_at)

            # 标签（最多显示 3 个）
            tags = getattr(skill_info, "tags", []) or []
            max_tags = 3
            visible_tags = tags[:max_tags]
            overflow_count = len(tags) - max_tags

            tag_controls = []
            for t in visible_tags:
                tag_controls.append(
                    ft.Container(
                        content=ft.Text(t, size=FONT_TAG, color=ft.Colors.ON_SURFACE_VARIANT),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        border_radius=4,
                        padding=ft.Padding(6, 2, 6, 2),
                    )
                )
            if overflow_count > 0:
                tag_controls.append(
                    ft.Text(f"+{overflow_count}", size=FONT_TAG, color=ft.Colors.OUTLINE)
                )
            controls.append(ft.Row(tag_controls, spacing=4, wrap=True))

            # 底部行：版本 + 分类 + 类型
            meta_items = [
                ft.Chip(label=ft.Text(skill_info.version, size=FONT_META), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=0),
                ft.Chip(label=ft.Text(skill_info.category or "misc", size=FONT_META), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=0),
            ]
            if type_label:
                meta_items.append(
                    ft.Chip(label=ft.Text(type_label, size=FONT_META), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=0),
                )
            controls.append(ft.Row(meta_items, spacing=4, wrap=True))

            # 安装时间
            if time_text:
                controls.append(
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[ft.Text(time_text, size=FONT_TAG, color=ft.Colors.OUTLINE)],
                    )
                )

        self.content = ft.Column(spacing=8, controls=controls)

    def _on_hover(self, e):
        """悬浮时提升阴影和边框。"""
        if e.data == "true":
            self.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=ft.Colors.with_opacity(0.12, ft.Colors.BLACK),
                offset=ft.Offset(0, 4),
            )
            self.border = ft.Border(
                left=ft.BorderSide(3, self._tag_color),
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.4, self._tag_color)),
                right=ft.BorderSide(1, ft.Colors.with_opacity(0.4, self._tag_color)),
                bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.4, self._tag_color)),
            )
            self.elevation = 4
        else:
            self.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=6,
                color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            )
            self.border = ft.Border(
                left=ft.BorderSide(3, self._tag_color),
                top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            )
            self.elevation = 2
        self.update()


class SkillListItem(ft.Container):
    """Skill 列表项组件（紧凑行布局）。"""

    def __init__(
        self,
        skill_info,
        on_click,
        checkbox_mode: bool = False,
        checked: bool = False,
        on_check=None,
        compact: bool = True,
    ):
        super().__init__()
        self.skill_info = skill_info
        tag_color = CATEGORY_COLORS.get(skill_info.category, ft.Colors.GREY)

        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        self.border_radius = 12
        self.padding = ft.Padding(12, 8, 12, 8)
        self.ink = True
        self.border = ft.Border(
            left=ft.BorderSide(3, tag_color),
            top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        )
        self.elevation = 1
        self.shadow = ft.BoxShadow(
            spread_radius=0,
            blur_radius=4,
            color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK),
            offset=ft.Offset(0, 1),
        )
        self.animate = ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT)
        self.on_click = lambda _: on_click(skill_info.name)
        self.on_hover = self._on_hover
        self._tag_color = tag_color

        # 类型图标
        skill_type = getattr(skill_info, "skill_type", "")
        type_icon, type_label = SKILL_TYPE_ICONS.get(skill_type, (ft.Icons.EXTENSION, ""))

        # 来源标识
        source = getattr(skill_info, "source", "")
        source_info = _source_info(source)

        # 复选框（批量模式）
        checkbox = None
        if checkbox_mode:
            checkbox = ft.Checkbox(
                value=checked,
                on_change=lambda e: on_check(skill_info.name, e.control.value) if on_check else None,
            )

        # 左侧：复选框（可选）+ 图标 + 名称 + 描述
        left_items = []
        if checkbox_mode:
            left_items.append(checkbox)
        left_items.extend([
            ft.Icon(type_icon, color=tag_color, size=20),
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text(skill_info.name, size=FONT_CARD_NAME, weight=ft.FontWeight.BOLD, color=tag_color),
                    ft.Text(
                        (skill_info.summary or skill_info.description or "")[:80],
                        size=FONT_CARD_DESC, color=ft.Colors.ON_SURFACE_VARIANT,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
            ),
        ])

        # 右侧：来源 + 详细模式下的额外信息
        right_items = [
            ft.Container(
                content=ft.Icon(source_info["icon"], size=14, color=source_info["color"]),
                tooltip=source_info["label"],
                border_radius=4,
                padding=ft.Padding(4, 1, 4, 1),
            ),
        ]

        if not compact:
            # 安装时间
            installed_at = getattr(skill_info, "installed_at", "")
            time_text = _relative_time(installed_at)

            # 标签（最多 2 个）
            tags = getattr(skill_info, "tags", []) or []
            visible_tags = tags[:2]
            overflow_count = len(tags) - 2

            tag_controls = []
            for t in visible_tags:
                tag_controls.append(
                    ft.Container(
                        content=ft.Text(t, size=FONT_TAG, color=ft.Colors.ON_SURFACE_VARIANT),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        border_radius=4,
                        padding=ft.Padding(4, 1, 4, 1),
                    )
                )
            if overflow_count > 0:
                tag_controls.append(ft.Text(f"+{overflow_count}", size=FONT_TAG, color=ft.Colors.OUTLINE))

            right_items = [
                ft.Row(tag_controls, spacing=4),
                ft.Text(skill_info.version, size=FONT_META, color=ft.Colors.OUTLINE),
            ] + right_items + [
                ft.Text(time_text, size=FONT_TAG, color=ft.Colors.OUTLINE) if time_text else ft.Container(),
            ]

        self.content = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(spacing=10, controls=left_items),
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=right_items,
                ),
            ],
        )

    def _on_hover(self, e):
        """悬浮时提升阴影。"""
        if e.data == "true":
            self.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=8,
                color=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            )
            self.elevation = 2
        else:
            self.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=4,
                color=ft.Colors.with_opacity(0.04, ft.Colors.BLACK),
                offset=ft.Offset(0, 1),
            )
            self.elevation = 1
        self.update()


class SearchBar(ft.Container):
    """搜索栏组件（带防抖）。"""

    def __init__(self, on_search, placeholder: str = "搜索 Skill...", debounce_ms: int = 300):
        super().__init__()
        self.on_search = on_search
        self.debounce_ms = debounce_ms
        self.padding = ft.Padding(0, 0, 0, 12)
        self._debounce_task = None

        self.content = ft.TextField(
            hint_text=placeholder,
            prefix_icon=ft.Icons.SEARCH,
            border=ft.InputBorder.OUTLINE,
            border_radius=8,
            on_change=self._on_change,
        )

    def _on_change(self, e):
        """输入变化时触发防抖搜索。"""
        value = e.control.value
        # 取消之前的防抖任务
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        # 创建新的防抖任务
        self._debounce_task = asyncio.create_task(self._debounced_search(value))

    async def _debounced_search(self, value: str):
        """防抖搜索：等待指定毫秒后执行。"""
        try:
            await asyncio.sleep(self.debounce_ms / 1000)
            self.on_search(value)
        except asyncio.CancelledError:
            pass


class TagCloud(ft.Container):
    """标签云组件：可视化热门标签，支持点击筛选。"""

    def __init__(
        self,
        skills: list,
        selected_tag: str = "",
        on_tag_click=None,
    ):
        super().__init__()
        self.skills = skills
        self.selected_tag = selected_tag
        self.on_tag_click = on_tag_click

        # 统计标签频率
        tag_counts: dict[str, int] = {}
        for s in skills:
            for tag in (getattr(s, "tags", None) or []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # 按频率降序排序，最多显示 15 个
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:15]

        if not sorted_tags:
            self.visible = False
            return

        # 计算字体大小范围（11-18）
        max_count = max(c for _, c in sorted_tags) if sorted_tags else 1
        min_count = min(c for _, c in sorted_tags) if sorted_tags else 1

        def _tag_size(count: int) -> float:
            if max_count == min_count:
                return 14
            ratio = (count - min_count) / (max_count - min_count)
            return 11 + ratio * 7

        tag_controls = []
        for tag, count in sorted_tags:
            is_selected = tag == selected_tag
            size = _tag_size(count)
            tag_controls.append(
                ft.Container(
                    content=ft.Text(
                        f"{tag} ({count})",
                        size=size,
                        weight=ft.FontWeight.W_500 if is_selected else ft.FontWeight.NORMAL,
                        color=ft.Colors.ON_PRIMARY if is_selected else ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    bgcolor=ft.Colors.PRIMARY if is_selected else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=12,
                    padding=ft.Padding(8, 4, 8, 4),
                    ink=True,
                    on_click=lambda _, t=tag: self._handle_click(t),
                )
            )

        self.content = ft.Column(
            spacing=8,
            controls=[
                ft.Text("热门标签", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
                ft.Row(wrap=True, spacing=6, run_spacing=6, controls=tag_controls),
            ],
        )

    def _handle_click(self, tag: str):
        if self.on_tag_click:
            # 点击已选中的标签取消选择
            new_tag = "" if tag == self.selected_tag else tag
            self.on_tag_click(new_tag)


class RecentUsage(ft.Container):
    """最近使用组件：显示最近访问的 Skill，支持收藏。"""

    def __init__(
        self,
        recent_skills: list,
        favorites: list[str],
        on_skill_click=None,
        on_favorite_toggle=None,
    ):
        super().__init__()
        self.recent_skills = recent_skills
        self.favorites = favorites
        self.on_skill_click = on_skill_click
        self.on_favorite_toggle = on_favorite_toggle

        if not recent_skills:
            self.visible = False
            return

        skill_controls = []
        for s in recent_skills[:5]:
            tag_color = CATEGORY_COLORS.get(s.category, ft.Colors.GREY)
            is_fav = s.name in favorites

            skill_controls.append(
                ft.Container(
                    content=ft.Row(
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.EXTENSION, color=tag_color, size=16),
                            ft.Text(
                                s.name,
                                size=FONT_CARD_NAME,
                                weight=ft.FontWeight.W_500,
                                color=tag_color,
                                expand=True,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.STAR if is_fav else ft.Icons.STAR_BORDER,
                                icon_size=16,
                                icon_color=ft.Colors.AMBER if is_fav else ft.Colors.OUTLINE,
                                on_click=lambda _, name=s.name: self._handle_favorite(name),
                            ),
                        ],
                    ),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    border_radius=8,
                    padding=ft.Padding(8, 4, 8, 4),
                    ink=True,
                    on_click=lambda _, name=s.name: self._handle_click(name),
                )
            )

        self.content = ft.Column(
            spacing=8,
            controls=[
                ft.Text("最近使用", size=FONT_SECTION, weight=ft.FontWeight.BOLD),
                ft.Column(spacing=4, controls=skill_controls),
            ],
        )

    def _handle_click(self, name: str):
        if self.on_skill_click:
            self.on_skill_click(name)

    def _handle_favorite(self, name: str):
        if self.on_favorite_toggle:
            self.on_favorite_toggle(name)


class EmptyState(ft.Container):
    """空状态占位组件。"""

    def __init__(self, on_install, on_create):
        super().__init__()
        self.expand = True
        self.alignment = ft.alignment.Alignment(0, 0)
        self.content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.EXPLORE_OUTLINED, size=72, color=ft.Colors.INDIGO),
                    padding=ft.Padding(24, 24, 24, 24),
                    border_radius=24,
                    bgcolor=ft.Colors.INDIGO_50,
                    shadow=ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=16,
                        color=ft.Colors.with_opacity(0.1, ft.Colors.INDIGO),
                        offset=ft.Offset(0, 4),
                    ),
                ),
                ft.Text("开始探索 Skills", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
                ft.Text("安装示例 Skill 或创建新的 Skill 来开始使用", size=FONT_SUBTITLE, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Row([
                    ft.FilledButton(
                        "安装 Skill",
                        icon=ft.Icons.FILE_DOWNLOAD,
                        on_click=lambda _: on_install(),
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.Padding(16, 12, 16, 12),
                        ),
                    ),
                    ft.OutlinedButton(
                        "新建 Skill",
                        icon=ft.Icons.ADD,
                        on_click=lambda _: on_create(),
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.Padding(16, 12, 16, 12),
                        ),
                    ),
                ], spacing=12),
            ],
        )


class SearchEmptyState(ft.Container):
    """搜索无结果空状态。"""

    def __init__(self, query: str, on_clear=None):
        super().__init__()
        self.expand = True
        self.alignment = ft.alignment.Alignment(0, 0)
        controls = [
            ft.Container(
                content=ft.Icon(ft.Icons.SEARCH_OFF, size=64, color=ft.Colors.INDIGO_200),
                padding=ft.Padding(20, 20, 20, 20),
                border_radius=20,
                bgcolor=ft.Colors.INDIGO_50,
            ),
            ft.Text(f"未找到与「{query}」匹配的 Skill", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
            ft.Text("尝试其他关键词，或清除筛选条件", size=FONT_SUBTITLE, color=ft.Colors.ON_SURFACE_VARIANT),
        ]
        if on_clear:
            controls.append(
                ft.OutlinedButton(
                    "清除筛选",
                    icon=ft.Icons.CLEAR_ALL,
                    on_click=lambda _: on_clear(),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(14, 10, 14, 10),
                    ),
                ),
            )
        self.content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=controls,
        )


class FilterEmptyState(ft.Container):
    """筛选无结果空状态。"""

    def __init__(self, on_clear=None):
        super().__init__()
        self.expand = True
        self.alignment = ft.alignment.Alignment(0, 0)
        controls = [
            ft.Container(
                content=ft.Icon(ft.Icons.FILTER_LIST_OFF, size=64, color=ft.Colors.INDIGO_200),
                padding=ft.Padding(20, 20, 20, 20),
                border_radius=20,
                bgcolor=ft.Colors.INDIGO_50,
            ),
            ft.Text("当前筛选条件下没有 Skill", size=FONT_TITLE, weight=ft.FontWeight.BOLD),
            ft.Text("尝试调整筛选条件，或查看全部 Skill", size=FONT_SUBTITLE, color=ft.Colors.ON_SURFACE_VARIANT),
        ]
        if on_clear:
            controls.append(
                ft.OutlinedButton(
                    "清除所有筛选",
                    icon=ft.Icons.CLEAR_ALL,
                    on_click=lambda _: on_clear(),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(14, 10, 14, 10),
                    ),
                ),
            )
        self.content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=controls,
        )
