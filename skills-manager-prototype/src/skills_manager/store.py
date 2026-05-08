"""本地存储管理。

管理已安装的 Skills，维护本地索引。
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from .ir import SkillIR
from .parser import parse_skill_md


class StoreError(Exception):
    """存储操作错误。"""


class Store:
    """本地 Skill 存储管理器。"""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path.home() / ".skills-manager"
        self.store_dir = self.base_dir / "store"
        self.index_path = self.base_dir / "index.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)

    # ── 安装 ──────────────────────────────────────────────

    def install(
        self,
        source: Path,
        name: str | None = None,
        force: bool = False,
    ) -> SimpleNamespace:
        """安装 Skill 到本地存储。

        Args:
            source: Skill 目录路径（必须包含 SKILL.md）。
            name: 自定义安装名，默认使用 IR 中的 name。
            force: 是否覆盖已有的同名 Skill。

        Returns:
            安装后的 Skill 信息。
        """
        skill_md = source / "SKILL.md"
        if not skill_md.exists():
            raise StoreError(f"No SKILL.md found in {source}")

        ir = parse_skill_md(skill_md)
        install_name = name or ir.name

        target = self.store_dir / install_name
        if target.exists() and not force:
            raise StoreError(
                f"'{install_name}' already installed. Use force=True to overwrite."
            )

        # 复制文件
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)

        # 写入安装元数据
        meta = {
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
        }
        (target / ".skill_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 更新索引
        self._update_index(install_name, ir, str(source))

        return self.get(install_name)

    def install_from_package(self, package_path: Path) -> SimpleNamespace:
        """从 .skill 包文件安装。"""
        import tarfile

        if not package_path.exists():
            raise StoreError(f"Package not found: {package_path}")

        # 解压到临时目录
        tmp_dir = self.base_dir / ".tmp"
        tmp_dir.mkdir(exist_ok=True)

        try:
            with tarfile.open(package_path, "r:gz") as tar:
                tar.extractall(tmp_dir)

            # 找到 SKILL.md 所在的目录
            skill_dir = self._find_skill_dir(tmp_dir)
            if not skill_dir:
                raise StoreError("No SKILL.md found in package")

            return self.install(skill_dir)
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    def _find_skill_dir(self, search_dir: Path) -> Path | None:
        """在目录树中查找包含 SKILL.md 的目录。"""
        for skill_md in search_dir.rglob("SKILL.md"):
            return skill_md.parent
        return None

    # ── 卸载 ──────────────────────────────────────────────

    def uninstall(self, name: str) -> None:
        """卸载 Skill。"""
        target = self.store_dir / name
        if target.exists():
            shutil.rmtree(target)
        self._remove_from_index(name)

    # ── 查询 ──────────────────────────────────────────────

    def list_all(self) -> list[SimpleNamespace]:
        """列出所有已安装 Skill。"""
        index = self._load_index()
        return [
            SimpleNamespace(name=k, **v) for k, v in index["skills"].items()
        ]

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

    # ── 搜索 ──────────────────────────────────────────────

    def search(
        self,
        query: str,
        tag: str | None = None,
        category: str | None = None,
    ) -> list[SimpleNamespace]:
        """搜索 Skills。"""
        results = []
        query_lower = query.lower()

        for skill in self.list_all():
            # 分类过滤
            if category and skill.category != category:
                continue
            # 标签过滤
            if tag and tag not in (skill.tags or []):
                continue
            # 关键词匹配
            searchable = " ".join([
                skill.name,
                skill.description or "",
                skill.summary or "",
                " ".join(skill.tags or []),
            ]).lower()
            if query_lower in searchable:
                results.append(skill)

        return results

    # ── 索引管理 ──────────────────────────────────────────

    def _load_index(self) -> dict:
        if self.index_path.exists():
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        return {"version": 1, "skills": {}}

    def _save_index(self, index: dict) -> None:
        self.index_path.write_text(
            json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _update_index(self, name: str, ir: SkillIR, source: str) -> None:
        index = self._load_index()
        index["skills"][name] = {
            "version": ir.version,
            "description": ir.description,
            "summary": ir.summary,
            "type": ir.type,
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
