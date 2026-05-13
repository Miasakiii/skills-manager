"""使用历史、导出历史、收藏。"""

from __future__ import annotations

from datetime import datetime, timezone

from ..logging import get_logger

logger = get_logger(__name__)


class _HistoryTracker:
    """历史记录与收藏 mixin。"""

    # -- 使用历史 ----------------------------------------------

    def get_usage_history(self) -> list[dict]:
        """获取使用历史记录。"""
        return self._read_json(self.base_dir / "usage_history.json", [])

    def add_usage(self, skill_name: str, action: str = "view") -> None:
        """添加使用记录。"""
        history = self.get_usage_history()
        history.append({
            "skill_name": skill_name,
            "action": action,
            "used_at": datetime.now(timezone.utc).isoformat(),
        })
        if len(history) > 200:
            history = history[-200:]
        self._write_json(self.base_dir / "usage_history.json", history)

    def get_recent_skills(self, limit: int = 5) -> list[str]:
        """获取最近使用的 Skill 名称列表（去重，按时间倒序）。"""
        history = self.get_usage_history()
        seen = set()
        recent = []
        for entry in reversed(history):
            name = entry.get("skill_name", "")
            if name and name not in seen:
                seen.add(name)
                recent.append(name)
            if len(recent) >= limit:
                break
        return recent

    # -- 收藏 ------------------------------------------------

    def get_favorites(self) -> list[str]:
        """获取收藏的 Skill 名称列表。"""
        return self._read_json(self.base_dir / "favorites.json", [])

    def toggle_favorite(self, skill_name: str) -> bool:
        """切换收藏状态。

        Returns:
            True 表示已收藏，False 表示已取消收藏。
        """
        favorites = self.get_favorites()
        if skill_name in favorites:
            favorites.remove(skill_name)
            is_fav = False
        else:
            favorites.append(skill_name)
            is_fav = True
        self._write_json(self.base_dir / "favorites.json", favorites)
        return is_fav

    def is_favorite(self, skill_name: str) -> bool:
        """检查 Skill 是否已收藏。"""
        return skill_name in self.get_favorites()

    # -- 导出历史 ----------------------------------------------

    def get_export_history(self) -> list[dict]:
        """获取导出历史记录。"""
        return self._read_json(self.base_dir / "export_history.json", [])

    def add_export_history(
        self,
        skill_name: str,
        format_name: str,
        output_path: str,
    ) -> None:
        """添加导出历史记录。"""
        history = self.get_export_history()
        history.append({
            "skill_name": skill_name,
            "format": format_name,
            "output_path": output_path,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        })
        if len(history) > 100:
            history = history[-100:]
        self._write_json(self.base_dir / "export_history.json", history)

    def clear_export_history(self) -> None:
        """清空导出历史记录。"""
        history_path = self.base_dir / "export_history.json"
        if history_path.exists():
            history_path.unlink()
