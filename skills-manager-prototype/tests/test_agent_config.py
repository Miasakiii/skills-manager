"""测试 Agent 配置生成器。"""



from skills_manager.agent_config import generate_claude_md, update_agent_claude_md


class TestGenerateClaudeMd:
    """测试 CLAUDE.md 内容生成。"""

    def test_empty_skills(self):
        content = generate_claude_md([])
        assert "暂无已安装的 skill" in content

    def test_single_skill(self):
        skills = [
            {"name": "translator", "skill_type": "component", "description": "翻译工具"}
        ]
        content = generate_claude_md(skills)
        assert "translator" in content
        assert "component" in content
        assert "翻译工具" in content
        assert "| 名称 | 类型 | 描述 |" in content

    def test_multiple_skills(self):
        skills = [
            {"name": "translator", "skill_type": "component", "description": "翻译工具"},
            {"name": "jtbd", "skill_type": "interactive", "description": "需求分析"},
        ]
        content = generate_claude_md(skills)
        assert "translator" in content
        assert "jtbd" in content
        assert content.count("|") >= 8  # 表头 + 分隔 + 2行数据

    def test_missing_fields(self):
        skills = [{"name": "test"}]
        content = generate_claude_md(skills)
        assert "test" in content

    def test_format(self):
        skills = [
            {"name": "a", "skill_type": "b", "description": "c"}
        ]
        content = generate_claude_md(skills)
        lines = content.strip().split("\n")
        # 检查表格格式
        assert lines[4] == "| 名称 | 类型 | 描述 |"
        assert lines[5] == "| ---- | ---- | ---- |"
        assert lines[6] == "| a | b | c |"


class TestUpdateAgentClaudeMd:
    """测试更新 agent 目录的 CLAUDE.md。"""

    def test_update_existing_dir(self, tmp_path):
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        skills = [
            {"name": "test", "skill_type": "component", "description": "Test"}
        ]
        result = update_agent_claude_md(agent_dir, skills)
        assert result is True
        claude_md = agent_dir / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text(encoding="utf-8")
        assert "test" in content

    def test_update_nonexistent_dir(self, tmp_path):
        agent_dir = tmp_path / "nonexistent"
        skills = [{"name": "test"}]
        result = update_agent_claude_md(agent_dir, skills)
        assert result is False

    def test_overwrite_existing(self, tmp_path):
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        claude_md = agent_dir / "CLAUDE.md"
        claude_md.write_text("Old content", encoding="utf-8")

        skills = [{"name": "new", "skill_type": "component", "description": "New"}]
        result = update_agent_claude_md(agent_dir, skills)
        assert result is True
        content = claude_md.read_text(encoding="utf-8")
        assert "Old content" not in content
        assert "new" in content
