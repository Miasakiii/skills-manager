"""本地存储管理。

管理已安装的 Skills，维护本地索引。
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from .ir import SkillIR
from .parser import parse_skill_md
from .validator import validate_skill_dir


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
        # 验证 skill 格式
        validation = validate_skill_dir(source)
        if not validation.valid:
            raise StoreError(f"验证失败: {'; '.join(validation.errors)}")

        skill_md = source / "SKILL.md"

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

        # 自动同步到各 agent 目录（symlink 优先，让 agent 立即可用）
        self.sync_skill_to_agents(install_name)

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

    # ── 自动发现 ──────────────────────────────────────────

    def discover_in_paths(self, scan_paths: list[Path]) -> list[Path]:
        """扫描预设路径，返回已发现但未安装的 Skill 目录列表。

        排除已安装的（按 name 匹配）和隐藏目录。
        """
        managed = {s.name for s in self.list_all()}
        discovered: list[Path] = []
        seen: set[str] = set()

        for scan_path in scan_paths:
            if not scan_path.is_dir():
                continue
            try:
                for item in sorted(scan_path.iterdir()):
                    if not item.is_dir() or item.name.startswith("."):
                        continue
                    if item.name in managed or item.name in seen:
                        continue
                    if (item / "SKILL.md").exists():
                        discovered.append(item)
                        seen.add(item.name)
            except PermissionError:
                continue

        return discovered

    # ── 扫描 ──────────────────────────────────────────────

    @staticmethod
    def scan_directory(root: Path) -> list[Path]:
        """递归扫描目录，返回所有包含 SKILL.md 的子目录路径。"""
        results = []
        for item in sorted(root.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                if (item / "SKILL.md").exists():
                    results.append(item)
                else:
                    # 递归扫描子目录
                    results.extend(Store.scan_directory(item))
        return results

    def scan_and_install(self, root: Path) -> tuple[list[str], list[tuple[str, str]]]:
        """扫描目录并批量安装所有发现的 Skill。

        Returns:
            (installed_names, failed_names_with_errors)
        """
        discovered = self.scan_directory(root)
        installed = []
        failed = []
        for skill_dir in discovered:
            try:
                result = self.install(skill_dir, force=True)
                installed.append(result.name)
            except Exception as e:
                failed.append((skill_dir.name, str(e)))
        return installed, failed

    # ── 卸载 ──────────────────────────────────────────────

    def uninstall(self, name: str) -> None:
        """卸载 Skill（同时清理各 agent 目录中的链接）。"""
        self.remove_skill_from_agents(name)
        target = self.store_dir / name
        if target.exists():
            shutil.rmtree(target)
        self._remove_from_index(name)

    # ── 同步到 Agent ──────────────────────────────────────

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
            raise StoreError(f"Skill 源目录不存在: {source}")
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
        # 目标已是有效 skill 目录（含 SKILL.md）→ 不覆盖，保护用户数据
        if dest.is_dir() and (dest / "SKILL.md").exists():
            return False

        # 清理旧的 symlink 或非 skill 目录
        try:
            if dest.is_symlink():
                dest.unlink()
            elif dest.exists():
                shutil.rmtree(dest)
        except (OSError, PermissionError):
            pass

        # 尝试 symlink
        try:
            dest.symlink_to(src.resolve(), target_is_directory=True)
            return True
        except (OSError, NotImplementedError):
            pass

        # 回退：复制
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
        skill_type: str | None = None,
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
            # 语义类型过滤
            if skill_type and getattr(skill, 'skill_type', '') != skill_type:
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

    # ── 监视路径管理 ──────────────────────────────────────

    def get_watch_paths(self) -> list[str]:
        """获取用户自定义的监视路径列表。"""
        path = self.base_dir / "watch_paths.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

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
        path = self.base_dir / "watch_paths.json"
        path.write_text(
            json.dumps(paths, indent=2, ensure_ascii=False), encoding="utf-8"
        )

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
