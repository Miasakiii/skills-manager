"""Skill 翻译。"""

from __future__ import annotations

from ..ir import SkillIR
from ..logging import get_logger
from ..parser import parse_skill_md
from ..translator import _detect_language, translate_skill_md
from .core import StoreError

logger = get_logger(__name__)


class _TranslationManager:
    """翻译管理 mixin。"""

    @staticmethod
    def _should_translate(ir: SkillIR) -> bool:
        """检测 IR 的 description 或 summary 是否需要翻译为中文。"""
        texts = [t for t in (ir.description, ir.summary) if t]
        return any(_detect_language(t) == "en" for t in texts)

    def translate_skill(self, name: str, target_lang: str | None = "zh-CN") -> bool:
        """翻译已安装 Skill 的 SKILL.md 中的描述。

        Args:
            name: Skill 名称。
            target_lang: 目标语言，None 时自动检测反向翻译。

        Returns:
            是否实际修改了内容。
        """
        skill_md_path = self.get_skill_md_path(name)
        if not skill_md_path.exists():
            raise StoreError(f"SKILL.md 不存在: '{name}'")

        content = skill_md_path.read_text(encoding="utf-8")
        translated = translate_skill_md(content, target_lang=target_lang)
        if translated == content:
            return False

        skill_md_path.write_text(translated, encoding="utf-8")
        ir = parse_skill_md(skill_md_path)
        index = self._load_index()
        if name in index["skills"]:
            index["skills"][name]["description"] = ir.description
            index["skills"][name]["summary"] = ir.summary
            self._save_index(index)
        logger.info("已翻译 Skill 描述: %s", name)
        return True
