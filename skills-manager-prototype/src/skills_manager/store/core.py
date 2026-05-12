"""Store 核心功能。

初始化、目录管理、索引管理、JSON 工具、基础查询、搜索、监视路径。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from ..ir import SkillIR
from ..logging import get_logger
from ..parser import parse_skill_md

logger = get_logger(__name__)


class StoreError(Exception):
    """存储操作错误。"""


class _StoreCore:
    """Store 核心 mixin（初始化、索引、查询）。"""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path.home() / ".skills-manager"
        self.store_dir = self.base_dir / "store"
        self.index_path = self.base_dir / "index.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)

    # -- 查询 ------------------------------------------------

    def list_all(self) -> list[SimpleNamespace]:
        """列出所有已安装 Skill。"""
        index = self._load_index()
        result = []
        stale = []
        for k, v in index["skills"].items():
            if not (self.store_dir / k).is_dir():
                stale.append(k)
                logger.debug("Skill 目录已不存在，自动清理: %s", k)
                continue
            result.append(SimpleNamespace(name=k, **v))
        if stale:
            for k in stale:
                del index["skills"][k]
            self._save_index(index)
        return result

    def get(self, name: str) -> SimpleNamespace:
        """获取单个 Skill 信息。"""
        index = self._load_index()
        if name not in index["skills"]:
            raise StoreError(f"Skill '{name}' not found")
        return SimpleNamespace(name=name, **index["skills"][name])

    def exists(self, name: str) -> bool:
        """检查 Skill 是否已安装。"""
        index = self._load_index()
        return name in index["skills"]

    def get_skill_md_path(self, name: str) -> Path:
        """获取 Skill 的 SKILL.md 文件路径。"""
        return self.store_dir / name / "SKILL.md"

    def get_skill_ir(self, name: str) -> SkillIR:
        """获取 Skill 的 IR（重新解析 SKILL.md）。"""
        path = self.get_skill_md_path(name)
        if not path.exists():
            raise StoreError(f"SKILL.md not found for '{name}'")
        return parse_skill_md(path)

    def get_skill_content(self, name: str) -> str:
        """获取 Skill 的 SKILL.md 原始内容。"""
        path = self.get_skill_md_path(name)
        if not path.exists():
            raise StoreError(f"SKILL.md not found for '{name}'")
        return path.read_text(encoding="utf-8")

    # -- 搜索 ------------------------------------------------

    def search(
        self,
        query: str,
        tag: str | None = None,
        category: str | None = None,
        skill_type: str | None = None,
    ) -> list[SimpleNamespace]:
        """搜索 Skills。"""
        results = []
        query_lower = query.lower()

        for skill in self.list_all():
            if category and skill.category != category:
                continue
            if tag and tag not in (skill.tags or []):
                continue
            if skill_type and getattr(skill, "skill_type", "") != skill_type:
                continue
            searchable = " ".join([
                skill.name,
                skill.description or "",
                skill.summary or "",
                " ".join(skill.tags or []),
            ]).lower()
            if query_lower in searchable:
                results.append(skill)

        return results

    # -- 监视路径管理 ------------------------------------------

    def get_watch_paths(self) -> list[str]:
        """获取用户自定义的监视路径列表。"""
        return self._read_json(self.base_dir / "watch_paths.json", [])

    def add_watch_path(self, watch_path: str) -> None:
        """添加一个监视路径。"""
        paths = self.get_watch_paths()
        if watch_path not in paths:
            paths.append(watch_path)
            self._save_watch_paths(paths)

    def remove_watch_path(self, watch_path: str) -> None:
        """移除一个监视路径。"""
        paths = self.get_watch_paths()
        if watch_path in paths:
            paths.remove(watch_path)
            self._save_watch_paths(paths)

    def _save_watch_paths(self, paths: list[str]) -> None:
        self._write_json(self.base_dir / "watch_paths.json", paths)

    # -- JSON 工具方法 -----------------------------------------

    def _read_json(self, path: Path, default=None):
        """读取 JSON 文件，不存在或解析失败返回默认值。"""
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return default if default is not None else []
        return default if default is not None else []

    def _write_json(self, path: Path, data) -> None:
        """写入 JSON 文件。"""
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # -- 索引管理 ----------------------------------------------

    def _load_index(self) -> dict:
        if hasattr(self, "_index_cache") and self._index_cache is not None:
            return self._index_cache
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("索引文件损坏，尝试从备份恢复")
                backup = self.index_path.with_suffix(".json.bak")
                if backup.exists():
                    try:
                        data = json.loads(backup.read_text(encoding="utf-8"))
                        logger.info("已从备份恢复索引")
                    except (json.JSONDecodeError, OSError):
                        data = {"version": 1, "skills": {}}
                        logger.warning("备份也损坏，使用空索引")
                else:
                    data = {"version": 1, "skills": {}}
        else:
            data = {"version": 1, "skills": {}}
        self._index_cache = data
        return data

    def _save_index(self, index: dict) -> None:
        text = json.dumps(index, indent=2, ensure_ascii=False)
        self.index_path.write_text(text, encoding="utf-8")
        backup = self.index_path.with_suffix(".json.bak")
        try:
            backup.write_text(text, encoding="utf-8")
        except OSError:
            pass
        self._index_cache = None

    def _update_index(self, name: str, ir: SkillIR, source: str) -> None:
        index = self._load_index()
        index["skills"][name] = {
            "version": ir.version,
            "description": ir.description,
            "summary": ir.summary,
            "type": ir.type,
            "skill_type": ir.skill_type,
            "intent": ir.intent,
            "tags": ir.tags,
            "category": ir.category,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "path": str(self.store_dir / name),
        }
        self._save_index(index)

    def _remove_from_index(self, name: str) -> None:
        index = self._load_index()
        index["skills"].pop(name, None)
        self._save_index(index)
