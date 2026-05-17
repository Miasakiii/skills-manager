"""使用历史、导出历史、收藏。"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from ..logging import get_logger

logger = get_logger(__name__)


def _parse_iso(ts: str) -> datetime | None:
    """容错地解析 ISO 时间字符串；失败时返回 None。"""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class _HistoryTracker:
    """历史记录与收藏 mixin。"""

    # -- 使用历史 ----------------------------------------------

    def get_usage_history(self) -> list[dict]:
        """获取使用历史记录。"""
        return self._read_json(self.base_dir / "usage_history.json", [])

    def add_usage(self, skill_name: str, action: str = "view") -> None:
        """添加使用记录。"""
        history = self.get_usage_history()
        history.append(
            {
                "skill_name": skill_name,
                "action": action,
                "used_at": datetime.now(timezone.utc).isoformat(),
            }
        )
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

    # -- 频率统计 ---------------------------------------------

    def get_usage_stats(
        self, window_days: int | None = None
    ) -> list[tuple[str, int]]:
        """按 Skill 统计使用次数，从高到低。

        Args:
            window_days: 若给定，仅统计最近 N 天内的记录；None 表示全部。

        Returns:
            ``[(skill_name, count), ...]``，按 count 倒序。
        """
        return _aggregate(
            self.get_usage_history(),
            key="skill_name",
            ts_key="used_at",
            window_days=window_days,
        )

    def get_export_stats(
        self, window_days: int | None = None
    ) -> list[tuple[str, int]]:
        """按 Skill 统计导出次数。"""
        return _aggregate(
            self.get_export_history(),
            key="skill_name",
            ts_key="exported_at",
            window_days=window_days,
        )

    def get_export_format_stats(
        self, window_days: int | None = None
    ) -> list[tuple[str, int]]:
        """按导出格式统计次数。"""
        return _aggregate(
            self.get_export_history(),
            key="format",
            ts_key="exported_at",
            window_days=window_days,
        )

    def get_top_skills(
        self, limit: int = 5, window_days: int | None = None
    ) -> list[tuple[str, int]]:
        """综合使用 + 导出的热门 Skill 排行（每次使用计 1 分、每次导出计 2 分）。

        若 Skill 已不在已安装索引中（已卸载），自动从结果中过滤。
        """
        scores: Counter[str] = Counter()
        for name, count in self.get_usage_stats(window_days):
            scores[name] += count
        for name, count in self.get_export_stats(window_days):
            scores[name] += count * 2

        # 过滤已卸载的 skill
        try:
            installed = {s.name for s in self.list_all()}
        except Exception:
            installed = None
        if installed is not None:
            scores = Counter(
                {k: v for k, v in scores.items() if k in installed}
            )

        return scores.most_common(limit)

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
        history.append(
            {
                "skill_name": skill_name,
                "format": format_name,
                "output_path": output_path,
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(history) > 100:
            history = history[-100:]
        self._write_json(self.base_dir / "export_history.json", history)

    def clear_export_history(self) -> None:
        """清空导出历史记录。"""
        history_path = self.base_dir / "export_history.json"
        if history_path.exists():
            history_path.unlink()


# ── 内部工具 ────────────────────────────────────────────


def _aggregate(
    entries: list[dict],
    *,
    key: str,
    ts_key: str,
    window_days: int | None = None,
) -> list[tuple[str, int]]:
    """按 ``key`` 字段聚合次数。``window_days`` 限定时间窗口。"""
    cutoff: datetime | None = None
    if window_days is not None and window_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    counter: Counter[str] = Counter()
    for entry in entries:
        value = entry.get(key) or ""
        if not value:
            continue
        if cutoff is not None:
            ts = _parse_iso(entry.get(ts_key, ""))
            if ts is None or ts < cutoff:
                continue
        counter[value] += 1
    return counter.most_common()
