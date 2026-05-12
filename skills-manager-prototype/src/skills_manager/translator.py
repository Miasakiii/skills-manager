"""翻译模块 — 将英文 Skill 介绍自动翻译为中文。"""

from __future__ import annotations

import json
import re
from urllib.request import Request, urlopen
from urllib.parse import quote

from .parser import _split_frontmatter


def _detect_language(text: str) -> str:
    """检测文本主要语言。返回 'en'、'zh' 或 'mixed'。"""
    if not text:
        return "en"
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return "en"
    ascii_count = sum(1 for c in alpha_chars if c.isascii())
    cjk_count = sum(1 for c in alpha_chars if '一' <= c <= '鿿')
    total = len(alpha_chars)
    if cjk_count / total > 0.3:
        return "zh"
    if ascii_count / total > 0.7:
        return "en"
    return "mixed"


def translate_text(text: str, target_lang: str | None = None) -> str:
    """翻译文本，依次尝试多个免费翻译后端。

    Args:
        text: 待翻译文本。
        target_lang: 目标语言代码（'zh-CN' 或 'en'）。None 时自动检测反向翻译。

    Returns:
        翻译后的文本。如果所有后端都失败，返回原文。
    """
    if not text or not text.strip():
        return text

    # 自动检测：中文→英文，英文→中文
    if target_lang is None:
        detected = _detect_language(text)
        target_lang = "en" if detected == "zh" else "zh-CN"

    # 后端 1: MyMemory
    result = _translate_mymemory(text, target_lang)
    if result and result != text:
        return result

    # 后端 2: Google Translate
    result = _translate_google(text, target_lang)
    if result and result != text:
        return result

    # 后端 3: Lingva
    result = _translate_lingva(text, target_lang)
    if result and result != text:
        return result

    return text


def _translate_mymemory(text: str, to_lang: str) -> str:
    """MyMemory 免费翻译 API。"""
    try:
        # MyMemory 需要明确的源语言
        detected = _detect_language(text)
        sl = "zh-CN" if detected == "zh" else "en"
        tl = to_lang
        lang_pair = f"{sl}|{tl}"
        url = (
            "https://api.mymemory.translated.net/get"
            "?q=" + quote(text) + "&langpair=" + lang_pair
        )
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        result = data.get("responseData", {}).get("translatedText", "")
        return result if result else text
    except Exception:
        return text


def _translate_google(text: str, to_lang: str) -> str:
    """Google Translate 免费接口。"""
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=auto&tl=" + to_lang + "&dt=t&q=" + quote(text)
        )
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        parts = []
        for segment in data[0]:
            if segment[0]:
                parts.append(segment[0])
        result = "".join(parts)
        return result if result else text
    except Exception:
        return text


def _translate_lingva(text: str, to_lang: str) -> str:
    """Lingva 翻译（Google Translate 反代）。"""
    try:
        lang_code = "zh_Hans" if to_lang == "zh-CN" else to_lang
        url = (
            "https://lingva.ml/api/v1/auto/" + lang_code + "/"
            + quote(text)
        )
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        result = data.get("translation", "")
        return result if result else text
    except Exception:
        return text


def translate_skill_md(content: str, target_lang: str | None = None) -> str:
    """翻译 SKILL.md 内容中的 description/summary。

    自动检测语言：中文→英文，英文→中文。
    处理单行值（description: xxx）和多行值（summary: | ...）。

    Args:
        content: SKILL.md 原始内容。
        target_lang: 目标语言，None 时自动检测。

    Returns:
        翻译后的 SKILL.md 内容。
    """
    frontmatter, body = _split_frontmatter(content)
    if not frontmatter:
        return content

    translated_lines = []
    in_multiline = False
    multiline_key = None
    multiline_value = []

    for line in frontmatter.split("\n"):
        # 检测多行值开始（key: | 或 key: >）
        multi_match = re.match(r'^(\w+)\s*:\s*[|>]\s*$', line)
        if multi_match and not in_multiline:
            in_multiline = True
            multiline_key = multi_match.group(1)
            multiline_value = []
            translated_lines.append(line)
            continue

        if in_multiline:
            stripped = line.rstrip("\n\r")
            if stripped == "":
                multiline_value.append("")
                translated_lines.append(line)
                continue
            if line and line[0] in (" ", "\t"):
                multiline_value.append(stripped)
                translated_lines.append(line)
                continue
            else:
                _flush_multiline(
                    translated_lines, multiline_key, multiline_value, target_lang
                )
                in_multiline = False
                multiline_key = None
                multiline_value = []

        # 单行值处理
        match = re.match(r'^(description|summary)\s*:\s*(.+)$', line)
        if match and not in_multiline:
            key = match.group(1)
            value = match.group(2).strip()
            value = value.strip('"').strip("'")
            detected = _detect_language(value)
            tl = target_lang or ("en" if detected == "zh" else "zh-CN")
            if tl == "en" and detected != "en":
                translated = translate_text(value, "en")
            elif tl == "zh-CN" and detected != "zh":
                translated = translate_text(value, "zh-CN")
            else:
                translated = value
            if translated != value:
                original = match.group(2).strip()
                if original.startswith('"') and original.endswith('"'):
                    line = f'{key}: "{translated}"'
                elif original.startswith("'") and original.endswith("'"):
                    line = f"{key}: '{translated}'"
                else:
                    line = f'{key}: "{translated}"'
        translated_lines.append(line)

    if in_multiline and multiline_key:
        _flush_multiline(
            translated_lines, multiline_key, multiline_value, target_lang
        )

    return "---\n" + "\n".join(translated_lines) + "\n---\n" + body


def _flush_multiline(
    lines: list[str], key: str, value_lines: list[str], target_lang: str | None
) -> None:
    """将多行值翻译后替换到 lines 中。"""
    full_value = "\n".join(value_lines)
    if key not in ("description", "summary"):
        return
    detected = _detect_language(full_value)
    tl = target_lang or ("en" if detected == "zh" else "zh-CN")
    if tl == "en" and detected != "en":
        translated = translate_text(full_value, "en")
    elif tl == "zh-CN" and detected != "zh":
        translated = translate_text(full_value, "zh-CN")
    else:
        translated = full_value
    if translated != full_value and value_lines:
        new_lines = translated.split("\n")
        lines[:] = lines[: -len(value_lines)]
        for nl in new_lines:
            lines.append(f"  {nl}")
