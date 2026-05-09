"""测试场景推荐引擎。"""

from skills_manager.recommend import recommend_skills


class TestRecommendSkills:
    """场景推荐测试。"""

    def test_recommend_empty_scenario(self):
        """测试空场景。"""
        results = recommend_skills("", [{"name": "test"}])
        assert results == []

    def test_recommend_empty_skills(self):
        """测试空 Skill 列表。"""
        results = recommend_skills("翻译", [])
        assert results == []

    def test_recommend_keyword_match(self):
        """测试关键词匹配。"""
        skills = [
            {"name": "translator", "description": "多语言翻译工具"},
            {"name": "code-reviewer", "description": "代码审查工具"},
        ]
        results = recommend_skills("我需要翻译文档", skills)
        assert len(results) > 0
        assert results[0].skill_name == "translator"

    def test_recommend_tag_match(self):
        """测试标签匹配。"""
        skills = [
            {"name": "translator", "description": "翻译", "tags": ["translation", "i18n"]},
            {"name": "code-reviewer", "description": "审查", "tags": ["code", "review"]},
        ]
        results = recommend_skills("需要 translation 功能", skills)
        assert len(results) > 0
        assert results[0].skill_name == "translator"

    def test_recommend_category_match(self):
        """测试分类匹配。"""
        skills = [
            {"name": "translator", "description": "翻译", "category": "language"},
            {"name": "code-reviewer", "description": "审查", "category": "code"},
        ]
        results = recommend_skills("需要处理代码", skills)
        assert len(results) > 0
        assert results[0].skill_name == "code-reviewer"

    def test_recommend_top_k(self):
        """测试返回数量限制。"""
        skills = [
            {"name": f"skill-{i}", "description": "测试"}
            for i in range(10)
        ]
        results = recommend_skills("测试", skills, top_k=3)
        assert len(results) <= 3

    def test_recommend_score_order(self):
        """测试分数排序。"""
        skills = [
            {"name": "low", "description": "翻译辅助工具"},
            {"name": "high", "description": "翻译工具", "tags": ["翻译"]},
        ]
        results = recommend_skills("翻译", skills)
        assert len(results) == 2
        assert results[0].skill_name == "high"
        assert results[0].score > results[1].score
