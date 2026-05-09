"""场景推荐引擎。"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Recommendation:
    """推荐结果。"""
    skill_name: str
    score: float
    reason: str


def _tokenize(text: str) -> set[str]:
    """分词：英文按空格，中文按字符（bigram）。"""
    text = text.lower()
    # 提取英文单词和中文字符
    words = set()

    # 英文单词
    english_words = re.findall(r'[a-z]+', text)
    words.update(english_words)

    # 中文字符和 bigram
    chinese_chars = re.findall(r'[一-鿿]', text)
    for char in chinese_chars:
        words.add(char)
    # bigram
    for i in range(len(chinese_chars) - 1):
        words.add(chinese_chars[i] + chinese_chars[i + 1])

    return words


def recommend_skills(
    scenario: str,
    skills: list[dict],
    top_k: int = 5,
) -> list[Recommendation]:
    """根据场景描述推荐最合适的 Skill。

    Args:
        scenario: 场景描述文本。
        skills: Skill 列表，每个元素包含 name, description, summary, tags, category。
        top_k: 返回前 K 个推荐。

    Returns:
        推荐结果列表，按分数降序排列。
    """
    if not scenario.strip() or not skills:
        return []

    scenario_lower = scenario.lower()
    scenario_words = _tokenize(scenario)

    results = []

    for skill in skills:
        score = 0.0
        reasons = []

        # 构建 Skill 的文本表示
        skill_text = " ".join([
            skill.get("name", ""),
            skill.get("description", ""),
            skill.get("summary", ""),
            " ".join(skill.get("tags", [])),
            skill.get("category", ""),
        ])

        skill_words = _tokenize(skill_text)

        # 1. 关键词匹配（权重：0.4）
        common_words = scenario_words & skill_words
        if common_words:
            keyword_score = len(common_words) / max(len(scenario_words), 1)
            score += keyword_score * 0.4
            # 只显示前 3 个匹配词
            display_words = list(common_words)[:3]
            reasons.append(f"关键词匹配: {', '.join(display_words)}")

        # 2. 标签匹配（权重：0.3）
        tags = skill.get("tags", [])
        tag_matches = []
        for tag in tags:
            if tag.lower() in scenario_lower:
                tag_matches.append(tag)
        if tag_matches:
            tag_score = len(tag_matches) / max(len(tags), 1)
            score += tag_score * 0.3
            reasons.append(f"标签匹配: {', '.join(tag_matches)}")

        # 3. 分类匹配（权重：0.2）
        category = skill.get("category", "")
        category_keywords = {
            "language": ["翻译", "语言", "文本", "i18n", "多语言"],
            "code": ["代码", "编程", "开发", "审查", "生成", "测试", "调试"],
            "data": ["数据", "分析", "可视化", "清洗", "转换", "统计"],
            "research": ["搜索", "检索", "摘要", "事实", "核查"],
            "writing": ["写作", "博客", "邮件", "文案", "创意"],
            "automation": ["自动化", "调度", "通知", "文件", "集成"],
            "agent": ["agent", "记忆", "规划", "推理", "工具"],
        }
        if category in category_keywords:
            cat_keywords = category_keywords[category]
            cat_matches = [kw for kw in cat_keywords if kw in scenario_lower]
            if cat_matches:
                score += 0.2
                reasons.append(f"分类匹配: {category}")

        # 4. 描述相似度（权重：0.1）
        description = skill.get("description", "")
        if description:
            desc_words = _tokenize(description)
            desc_common = scenario_words & desc_words
            if desc_common:
                desc_score = len(desc_common) / max(len(scenario_words), 1)
                score += desc_score * 0.1

        if score > 0:
            reason = "; ".join(reasons) if reasons else "相关 Skill"
            results.append(Recommendation(
                skill_name=skill.get("name", ""),
                score=round(score, 3),
                reason=reason,
            ))

    # 按分数降序排列
    results.sort(key=lambda x: x.score, reverse=True)

    return results[:top_k]
