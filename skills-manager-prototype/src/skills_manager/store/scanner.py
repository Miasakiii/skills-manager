"""Skill 扫描与自动发现。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ..parser import parse_skill_md
from .core import StoreError


class _Scanner:
    """Skill 扫描与发现 mixin。"""

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

    @staticmethod
    def scan_directory(root: Path) -> list[Path]:
        """递归扫描目录，返回所有包含 SKILL.md 的子目录路径。"""
        results = []
        for item in sorted(root.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                if (item / "SKILL.md").exists():
                    results.append(item)
                else:
                    results.extend(_Scanner.scan_directory(item))
        return results

    def scan_and_install(self, root: Path) -> tuple[list[str], list[tuple[str, str]]]:
        """扫描目录并批量安装所有发现的 Skill。"""
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

    def scan_directory_with_info(self, root: Path) -> list[dict]:
        """扫描目录，返回每个 Skill 的详细信息。"""
        discovered = self.scan_directory(root)
        results = []
        for skill_dir in discovered:
            skill_md = skill_dir / "SKILL.md"
            try:
                ir = parse_skill_md(skill_md)
                results.append({
                    "path": skill_dir,
                    "name": ir.name,
                    "version": ir.version,
                    "description": ir.description,
                    "installed": self.exists(ir.name),
                })
            except Exception:
                results.append({
                    "path": skill_dir,
                    "name": skill_dir.name,
                    "version": "",
                    "description": "解析失败",
                    "installed": False,
                })
        return results
