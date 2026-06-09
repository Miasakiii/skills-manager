"""Cursor Design 设计 Token 中心。

基于 Cursor 的设计语言：暖羊皮纸底色 + 深咖啡墨色 + 焦橙点缀。
所有颜色、字体、间距、圆角、阴影统一在此定义，供全项目引用。
"""

import flet as ft


# ── 颜色 ──────────────────────────────────────────────


def _hex(hex_str: str) -> str:
    """确保颜色字符串带 # 前缀。"""
    return hex_str if hex_str.startswith("#") else f"#{hex_str}"


# Light mode 调色板
COLORS = {
    # 主色 / 文字
    "primary": _hex("#26251e"),  # 深咖啡墨色
    "on_primary": _hex("#f7f7f4"),  # 暖白
    # 强调色（仅用于高信号交互：CTA、badge、accent 按钮）
    "accent": _hex("#f54e00"),  # 焦橙
    "accent_soft": "rgba(245, 78, 0, 0.1)",  # 焦橙 10% 透明度
    # 文字层级
    "ink": _hex("#26251e"),  # 主文字
    "ink_secondary": "rgba(38, 37, 30, 0.6)",  # 次要文字
    "ink_tertiary": "rgba(38, 37, 30, 0.4)",  # 三级文字
    "ink_muted": "rgba(38, 37, 30, 0.5)",  # 弱化文字
    # 画布 / 表面
    "canvas": _hex("#f7f7f4"),  # 暖羊皮纸（主背景）
    "canvas_soft": _hex("#f2f1ed"),  # 柔和背景
    "canvas_muted": _hex("#ebeae5"),  # 更暗的背景
    "card": _hex("#f0efeb"),  # 卡片背景
    "card_hover": _hex("#ebeae5"),  # 卡片悬浮
    "card_warm": _hex("#f3ede6"),  # 暖色卡片
    # 边框
    "border_01": "rgba(38, 37, 30, 0.025)",  # 最轻边框
    "border_02": "rgba(38, 37, 30, 0.1)",  # 标准边框
    "border_03": "rgba(38, 37, 30, 0.6)",  # 强调边框
    # 语义色
    "success": _hex("#1f8a65"),
    "error": _hex("#cf2d56"),
    "warning": _hex("#d29922"),
    "info": _hex("#206595"),
    "link": _hex("#206595"),
}

# Dark mode 调色板
DARK_COLORS = {
    "canvas": _hex("#14120b"),
    "canvas_soft": _hex("#1b1913"),
    "card": _hex("#1b1913"),
    "card_02": _hex("#1d1b15"),
    "card_03": _hex("#201e18"),
    "card_04": _hex("#26241e"),
    "card_hover": _hex("#201e18"),
    "ink": _hex("#edecec"),
    "ink_secondary": "rgba(237, 236, 236, 0.6)",
    "ink_tertiary": "rgba(237, 236, 236, 0.4)",
    "border": "rgba(237, 236, 236, 0.1)",
    "border_strong": "rgba(237, 236, 236, 0.2)",
    "accent": _hex("#f54e00"),  # 强调色暗色模式不变
}


# ── 字体大小 ──────────────────────────────────────────────

# 字体栈（Cursor Gothic 不可用，使用系统 UI 字体回退）
FONT_FAMILY_UI = (
    "Inter, Segoe UI, Microsoft YaHei UI, PingFang SC, "
    "Noto Sans SC, system-ui, -apple-system, sans-serif"
)
FONT_FAMILY_MONO = (
    "Berkeley Mono, Cascadia Code, SFMono-Regular, Menlo, "
    "Monaco, Consolas, 'Liberation Mono', monospace"
)
FONT_FAMILY_DISPLAY = (
    "EB Garamond, Iowan Old Style, Palatino Linotype, "
    "URW Palladio L, P052, ui-serif, Georgia, Cambria, serif"
)

# 字号层级（对应 Cursor Design typography）
FONT_DISPLAY_XL = 64  # 展示标题 XL
FONT_DISPLAY_LG = 48  # 展示标题 LG
FONT_DISPLAY_MD = 36  # 展示标题 MD
FONT_DISPLAY_SM = 28  # 展示标题 SM
FONT_HEADING_LG = 22  # 大标题
FONT_HEADING_MD = 18  # 中标题
FONT_BODY_LG = 18  # 大正文
FONT_BODY = 16  # 正文
FONT_BODY_SM = 14  # 小正文
FONT_CAPTION = 12  # 说明文字（大写）
FONT_SMALL = 11  # 小字
FONT_TAG = 11  # 标签
FONT_META = 12  # 元数据

# 保持向后兼容的别名（减少页面文件改动量）
FONT_DISPLAY = FONT_DISPLAY_SM
FONT_TITLE = FONT_HEADING_LG
FONT_HEADLINE = FONT_HEADING_MD
FONT_SECTION = FONT_BODY
FONT_SUBTITLE = FONT_BODY_SM
FONT_CARD_NAME = FONT_BODY
FONT_CARD_DESC = FONT_CAPTION


# ── 圆角 ──────────────────────────────────────────────

RADIUS_XS = 3  # 小元素
RADIUS_SM = 6  # 按钮、小卡片
RADIUS_MD = 8  # 按钮、输入框
RADIUS_LG = 10  # 卡片
RADIUS_XL = 16  # 大卡片
RADIUS_PILL = 9999  # 药丸形状


# ── 间距 ──────────────────────────────────────────────

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24
SPACE_XXL = 32
SPACE_SECTION = 96  # 区块间距


# ── 阴影 ──────────────────────────────────────────────

# Cursor 风格：卡片无阴影，仅浮动面板有阴影
SHADOW_NONE = None
SHADOW_WINDOW = ft.BoxShadow(
    spread_radius=0,
    blur_radius=70,
    color="rgba(0, 0, 0, 0.3)",
    offset=ft.Offset(0, 22),
)
SHADOW_MODAL = ft.BoxShadow(
    spread_radius=0,
    blur_radius=70,
    color="rgba(0, 0, 0, 0.14)",
    offset=ft.Offset(0, 28),
)


# ── 分类颜色映射 ──────────────────────────────────────
# 保持语义色但调低饱和度，匹配 Cursor 的克制调色

CATEGORY_COLORS = {
    "language": _hex("#206595"),  # info blue
    "code": _hex("#1f8a65"),  # success green
    "data": _hex("#d29922"),  # warning amber
    "research": _hex("#aa52a2"),  # muted purple
    "writing": _hex("#267f99"),  # cyan
    "automation": _hex("#cf2d56"),  # error red
    "misc": _hex("#7a7a7a"),  # muted
    "agent": _hex("#f54e00"),  # accent orange
}


# ── Flet ColorScheme 构建 ──────────────────────────────


def build_light_color_scheme() -> ft.ColorScheme:
    """构建 Cursor Design 浅色模式的 ColorScheme。"""
    return ft.ColorScheme(
        primary=COLORS["primary"],
        on_primary=COLORS["on_primary"],
        primary_container=COLORS["card"],
        on_primary_container=COLORS["ink"],
        secondary=COLORS["accent"],
        on_secondary=COLORS["on_primary"],
        secondary_container=COLORS["accent_soft"],
        on_secondary_container=COLORS["accent"],
        surface=COLORS["canvas"],
        surface_container=COLORS["card"],
        surface_container_highest=COLORS["canvas_muted"],
        on_surface=COLORS["ink"],
        on_surface_variant=COLORS["ink_secondary"],
        outline=COLORS["border_02"],
        outline_variant=COLORS["border_01"],
        error=COLORS["error"],
        on_error=COLORS["on_primary"],
        error_container=_hex("#fde0e6"),
        on_error_container=COLORS["error"],
    )


def build_dark_color_scheme() -> ft.ColorScheme:
    """构建 Cursor Design 暗色模式的 ColorScheme。"""
    return ft.ColorScheme(
        primary=DARK_COLORS["ink"],
        on_primary=DARK_COLORS["canvas"],
        primary_container=DARK_COLORS["card_02"],
        on_primary_container=DARK_COLORS["ink"],
        secondary=DARK_COLORS["accent"],
        on_secondary=DARK_COLORS["ink"],
        secondary_container=DARK_COLORS["card_03"],
        on_secondary_container=DARK_COLORS["accent"],
        surface=DARK_COLORS["canvas"],
        surface_container=DARK_COLORS["card"],
        surface_container_highest=DARK_COLORS["card_04"],
        on_surface=DARK_COLORS["ink"],
        on_surface_variant=DARK_COLORS["ink_secondary"],
        outline=DARK_COLORS["border"],
        outline_variant=DARK_COLORS["border"],
        error=_hex("#f06292"),
        on_error=DARK_COLORS["canvas"],
        error_container=_hex("#5c1a2e"),
        on_error_container=_hex("#f06292"),
    )


def get_theme(mode: str = "light") -> ft.Theme:
    """返回完整配置好的 Flet Theme 对象。"""
    if mode == "dark":
        return ft.Theme(
            font_family=FONT_FAMILY_UI,
            color_scheme=build_dark_color_scheme(),
        )
    return ft.Theme(
        font_family=FONT_FAMILY_UI,
        color_scheme=build_light_color_scheme(),
    )
