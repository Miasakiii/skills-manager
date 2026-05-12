"""Agent 目录同步。"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..logging import get_logger
from .core import StoreError

logger = get_logger(__name__)


class _AgentSync:
    """Agent 目录同步 mixin。"""

    @staticmethod
    def get_agent_skills_dirs() -> list[Path]:
        """返回所有存在的 agent skills 目录（存在才返回，用于创建链接）。"""
        home = Path.home()
        candidates = [
            home / ".cc-switch" / "skills",
            home / ".claude" / "skills",
            home / ".codex" / "skills",
            home / ".gemini" / "skills",
            home / ".config" / "opencode" / "skills",
            home / ".openclaw" / "skills",
            home / ".agents" / "skills",
        ]
        claude_desktop = home / ".claude-desktop" / "skills"
        if claude_desktop.is_dir():
            candidates.append(claude_desktop)
        return [d for d in candidates if d.is_dir()]

    def sync_skill_to_agents(self, name: str) -> dict[str, bool]:
        """将指定 Skill 同步（symlink）到所有 agent 目录。

        返回 {agent_dir_name: is_symlink} 字典。
        """
        source = self.store_dir / name
        if not source.is_dir():
            raise StoreError(f"Skill source directory does not exist: {source}")
        results: dict[str, bool] = {}
        for agent_dir in self.get_agent_skills_dirs():
            dest = agent_dir / name
            is_link = self._create_link(source, dest)
            results[agent_dir.name] = is_link
        return results

    def remove_skill_from_agents(self, name: str) -> None:
        """从所有 agent 目录中移除 Skill 的链接或副本。"""
        for agent_dir in self.get_agent_skills_dirs():
            self._remove_link(agent_dir / name)

    @staticmethod
    def _create_link(src: Path, dest: Path) -> bool:
        """创建目录符号链接。优先 symlink（省磁盘），权限不足时回退复制。

        返回 True 表示 symlink 成功，False 表示回退到复制或跳过。
        """
        if dest.is_dir() and (dest / "SKILL.md").exists():
            return False

        try:
            if dest.is_symlink():
                dest.unlink()
            elif dest.exists():
                shutil.rmtree(dest)
        except (OSError, PermissionError):
            pass

        try:
            dest.symlink_to(src.resolve(), target_is_directory=True)
            return True
        except (OSError, NotImplementedError):
            pass

        try:
            shutil.copytree(src, dest)
        except (OSError, shutil.Error):
            pass
        return False

    @staticmethod
    def _remove_link(dest: Path) -> None:
        """删除符号链接或复制的目录。"""
        try:
            if dest.is_symlink():
                dest.unlink()
            elif dest.is_dir():
                shutil.rmtree(dest)
        except (OSError, PermissionError):
            pass
