"""Skill 自动分类。"""

from __future__ import annotations

from ..ir import SkillIR
from ..logging import get_logger
from .core import StoreError

logger = get_logger(__name__)


class _CategoryManager:
    """自动分类 mixin。"""

    STANDARD_CATEGORIES = {
        "language", "code", "data", "research", "writing",
        "automation", "agent", "misc",
    }

    CATEGORY_REMAP = {
        "development": "code", "programming": "code",
        "backend": "code", "mobile": "code",
        "testing": "code", "qa": "code", "quality": "code",
        "security": "code",
        "devops": "automation", "deployment": "automation",
        "infrastructure": "automation", "monitoring": "automation",
        "cloud": "automation", "ci/cd": "automation", "logging": "automation",
        "database": "data",
        "design": "misc", "ui": "misc", "ux": "misc", "frontend": "misc",
        "video": "misc", "audio": "misc", "image": "misc", "media": "misc",
        "art": "misc",
        "career": "misc", "coaching": "misc", "education": "misc",
        "business": "misc", "finance": "misc", "legal": "misc",
        "healthcare": "misc", "health": "misc", "medical": "misc",
        "productivity": "misc", "communication": "writing",
    }

    CATEGORY_KEYWORDS = {
        "code": [
            "code", "program", "develop", "api", "sdk", "git", "debug", "refactor",
            "python", "javascript", "typescript", "rust", "golang", "java", "c++", "cpp",
            "kotlin", "swift", "dart", "flutter", "react", "vue", "angular", "node",
            "express", "fastapi", "django", "spring", "laravel", "next", "nuxt",
            "nestjs", "postgres", "sql", "docker", "kubernetes", "pattern",
            "coding", "architect", "hexagonal", "backend", "mobile",
            "test", "tdd", "qa", "secur", "vulnerab", "compliance", "auth",
            "代码", "编程", "开发", "架构", "测试", "安全",
        ],
        "language": [
            "translat", "language", "i18n", "locale", "翻译", "多语言", "国际化",
        ],
        "data": [
            "data", "analy", "chart", "csv", "excel", "report", "dashboard",
            "metric", "statistic", "warehouse", "database",
            "数据", "分析", "报表", "图表",
        ],
        "research": [
            "search", "research", "retriev", "query", "knowledge", "rag",
            "deep research", "health", "medical", "clinical", "patient",
            "搜索", "研究", "检索", "知识", "医疗",
        ],
        "writing": [
            "write", "content", "doc", "blog", "copy", "article",
            "writing", "documentation", "communication",
            "写作", "文档", "文章", "文案",
        ],
        "automation": [
            "automat", "deploy", "ci", "cd", "pipeline", "workflow",
            "devops", "infrastructure", "orchestrat", "monitoring",
            "cloud", "logging", "billing", "procurement", "logistics",
            "inventory", "supply", "pricing",
            "自动化", "部署", "流水线", "运维",
        ],
        "agent": [
            "agent", "mcp", "harness", "loop",
            "代理", "自主",
        ],
    }

    @staticmethod
    def _normalize_category(category: str | None) -> str | None:
        """将非标准分类映射到标准分类。"""
        if not category:
            return None
        cat = category.lower().strip()
        if cat in _CategoryManager.STANDARD_CATEGORIES:
            return cat
        return _CategoryManager.CATEGORY_REMAP.get(cat)

    def _infer_category(self, ir: SkillIR) -> str | None:
        """根据关键词推断 Skill 分类。"""
        if ir.category:
            normalized = self._normalize_category(ir.category)
            if normalized:
                return normalized

        texts = []
        if ir.name:
            texts.append(ir.name.lower())
        if ir.description:
            texts.append(ir.description.lower())
        if ir.summary:
            texts.append(ir.summary.lower())
        if ir.tags:
            texts.extend(t.lower() for t in ir.tags)
        combined = " ".join(texts)

        scores: dict[str, int] = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[category] = score

        if not scores:
            return None

        return max(scores, key=scores.get)

    def reclassify_all(self) -> int:
        """对所有已安装 Skill 重新运行分类（标准化 + 推断）。

        Returns:
            被修改的 Skill 数量。
        """
        changed = 0
        for skill in self.list_all():
            name = skill.name
            current_category = getattr(skill, "category", None)

            normalized = self._normalize_category(current_category)
            if normalized and normalized != current_category:
                self._update_index_category(name, normalized)
                changed += 1
                continue

            if not normalized:
                try:
                    ir = self.get_skill_ir(name)
                    inferred = self._infer_category(ir)
                    if inferred and inferred != current_category:
                        self._update_index_category(name, inferred)
                        changed += 1
                except Exception:
                    continue

        return changed

    def _update_index_category(self, name: str, category: str) -> None:
        """更新索引中单个 Skill 的分类。"""
        index = self._load_index()
        if name in index["skills"]:
            index["skills"][name]["category"] = category
            self._save_index(index)
