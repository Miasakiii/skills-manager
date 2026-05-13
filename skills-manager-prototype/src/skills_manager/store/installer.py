"""Skill 安装与版本管理。

本地安装、包安装、URL/GitHub 安装、升级、更新、回滚、版本历史。
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from ..ir import SkillIR
from ..logging import get_logger
from ..parser import parse_skill_md
from ..security import sanitize_name, validate_path_safety
from ..validator import validate_skill_dir
from .core import StoreError

logger = get_logger(__name__)


class _SkillInstaller:
    """Skill 安装与版本管理 mixin。"""

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
        validation = validate_skill_dir(source)
        if not validation.valid:
            logger.warning("安装验证失败: %s — %s", source, "; ".join(validation.errors))
            raise StoreError(f"Validation failed: {'; '.join(validation.errors)}")

        skill_md = source / "SKILL.md"
        ir = parse_skill_md(skill_md)

        if not ir.category:
            ir.category = self._infer_category(ir)

        install_name = sanitize_name(name or ir.name)
        target = self.store_dir / install_name
        if not validate_path_safety(target, self.store_dir):
            raise StoreError(f"Unsafe skill name: {install_name}")

        if target.exists() and not force:
            raise StoreError(
                f"'{install_name}' already installed. Use force=True to overwrite."
            )

        if target.exists():
            if force:
                self._backup_current_version(install_name)
            shutil.rmtree(target)
        shutil.copytree(source, target)

        meta = {
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
        }
        (target / ".skill_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        history = self.get_version_history(install_name)
        history.append({
            "version": ir.version,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "description": ir.description,
        })
        self._save_version_history(install_name, history)

        self._update_index(install_name, ir, str(source))
        self.sync_skill_to_agents(install_name)

        logger.info("已安装 Skill: %s v%s (来源: %s)", install_name, ir.version, source)
        return self.get(install_name)

    def install_from_package(self, package_path: Path) -> SimpleNamespace:
        """从 .skill 包文件安装。"""
        import tarfile

        if not package_path.exists():
            raise StoreError(f"Package not found: {package_path}")

        tmp_dir = self.base_dir / ".tmp"
        tmp_dir.mkdir(exist_ok=True)

        try:
            with tarfile.open(package_path, "r:gz") as tar:
                tar.extractall(tmp_dir, filter="data" if hasattr(tarfile, "data_filter") else None)

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

    def install_from_url(self, url: str) -> SimpleNamespace:
        """从 URL 安装 Skill。"""
        try:
            import httpx
        except ImportError:
            raise StoreError(
                "需要安装 httpx：pip install skills-manager[remote]"
            )

        tmp_dir = self.base_dir / ".tmp"
        tmp_dir.mkdir(exist_ok=True)

        try:
            if "github.com" in url and not url.endswith((".skill", ".tar.gz", ".zip")):
                return self._install_from_github(url, tmp_dir)
            return self._install_from_file_url(url, tmp_dir)
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    def _install_from_file_url(self, url: str, tmp_dir: Path) -> SimpleNamespace:
        """从文件 URL 安装。"""
        import httpx

        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()

        file_name = url.split("/")[-1] or "download"
        file_path = tmp_dir / file_name
        file_path.write_bytes(response.content)

        if file_name.endswith(".skill"):
            return self.install_from_package(file_path)
        if file_name.endswith((".tar.gz", ".tgz", ".zip")):
            return self._install_from_archive(file_path, tmp_dir)

        raise StoreError(f"Unsupported file format: {file_name}")

    def _install_from_github(self, url: str, tmp_dir: Path) -> SimpleNamespace:
        """从 GitHub 仓库安装。"""
        import httpx

        parts = url.replace("https://github.com/", "").strip("/").split("/")
        if len(parts) < 2:
            raise StoreError(f"Invalid GitHub URL: {url}")

        user, repo = parts[0], parts[1]
        branch = "main"
        sub_path = ""

        if len(parts) > 3 and parts[2] == "tree":
            branch = parts[3] if len(parts) > 3 else "main"
            sub_path = "/".join(parts[4:]) if len(parts) > 4 else ""

        zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
        response = httpx.get(zip_url, follow_redirects=True, timeout=30)
        response.raise_for_status()

        zip_path = tmp_dir / "repo.zip"
        zip_path.write_bytes(response.content)

        import zipfile
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)

        extracted_dir = tmp_dir / f"{repo}-{branch}"
        search_dir = extracted_dir / sub_path if sub_path else extracted_dir

        skill_dir = self._find_skill_dir(search_dir)
        if not skill_dir:
            raise StoreError("No SKILL.md found in GitHub repository")

        return self.install(skill_dir)

    def _install_from_archive(self, archive_path: Path, tmp_dir: Path) -> SimpleNamespace:
        """从压缩包安装。"""
        import tarfile
        import zipfile

        extract_dir = tmp_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)

        if archive_path.name.endswith(".zip"):
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(extract_dir)
        else:
            with tarfile.open(archive_path) as tf:
                tf.extractall(extract_dir, filter="data" if hasattr(tarfile, "data_filter") else None)

        skill_dir = self._find_skill_dir(extract_dir)
        if not skill_dir:
            raise StoreError("No SKILL.md found in archive")

        return self.install(skill_dir)

    def uninstall(self, name: str) -> None:
        """卸载 Skill（同时清理各 agent 目录中的链接）。"""
        self.remove_skill_from_agents(name)
        target = self.store_dir / name
        if target.exists():
            shutil.rmtree(target)
        self._remove_from_index(name)
        logger.info("已卸载 Skill: %s", name)

    def get_version_history(self, name: str) -> list[dict]:
        """获取 Skill 的版本历史。"""
        history_path = self.store_dir / name / ".version_history.json"
        if history_path.exists():
            try:
                return json.loads(history_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_version_history(self, name: str, history: list[dict]) -> None:
        """保存版本历史。"""
        history_path = self.store_dir / name / ".version_history.json"
        history_path.write_text(
            json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _backup_current_version(self, name: str) -> None:
        """备份当前版本到 versions 目录。"""
        skill_dir = self.store_dir / name
        if not skill_dir.exists():
            return

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return

        ir = parse_skill_md(skill_md)
        versions_dir = skill_dir / ".versions"
        versions_dir.mkdir(exist_ok=True)

        version_name = ir.version.replace(".", "_")
        snapshot_dir = versions_dir / f"v{version_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        snapshot_dir.mkdir(exist_ok=True)

        for item in skill_dir.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_file():
                shutil.copy2(item, snapshot_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, snapshot_dir / item.name)

        history = self.get_version_history(name)
        history.append({
            "version": ir.version,
            "snapshot": snapshot_dir.name,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "description": ir.description,
        })
        self._save_version_history(name, history)

    def upgrade(self, name: str, source: Path) -> SimpleNamespace:
        """升级 Skill 到新版本。"""
        if not (self.store_dir / name).exists():
            raise StoreError(f"Skill '{name}' not installed")

        validation = validate_skill_dir(source)
        if not validation.valid:
            raise StoreError(f"Validation failed: {'; '.join(validation.errors)}")

        new_ir = parse_skill_md(source / "SKILL.md")
        self._backup_current_version(name)
        history = self.get_version_history(name)

        target = self.store_dir / name
        versions_dir = target / ".versions"
        versions_tmp = self.base_dir / ".versions_tmp" / name
        if versions_dir.exists():
            versions_tmp.parent.mkdir(parents=True, exist_ok=True)
            if versions_tmp.exists():
                shutil.rmtree(versions_tmp)
            shutil.move(str(versions_dir), str(versions_tmp))

        shutil.rmtree(target)
        shutil.copytree(source, target)

        if versions_tmp.exists():
            shutil.move(str(versions_tmp), str(versions_dir))

        meta = {
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "upgraded": True,
        }
        (target / ".skill_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        history.append({
            "version": new_ir.version,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "description": new_ir.description,
        })
        self._save_version_history(name, history)

        self._update_index(name, new_ir, str(source))
        self.sync_skill_to_agents(name)

        logger.info("已升级 Skill: %s → v%s", name, new_ir.version)
        return self.get(name)

    def update(self, name: str) -> SimpleNamespace:
        """从原始来源重新安装最新版本。"""
        skill_info = self.get(name)
        source = getattr(skill_info, "source", "")

        if not source:
            raise StoreError(f"Skill '{name}' has no source information, cannot update")

        if source.startswith(("http://", "https://", "github:")):
            return self.install_from_url(source)

        source_path = Path(source)
        if not source_path.exists():
            raise StoreError(f"Source directory does not exist: {source}")

        return self.upgrade(name, source_path)

    def can_update(self, name: str) -> tuple[bool, str]:
        """检查 Skill 是否可以更新。"""
        try:
            skill_info = self.get(name)
        except StoreError:
            return False, "Skill not found"

        source = getattr(skill_info, "source", "")
        if not source:
            return False, "No source information"

        if source.startswith(("http://", "https://", "github:")):
            return True, f"Source: {source}"

        source_path = Path(source)
        if source_path.exists():
            return True, f"来源: {source_path}"
        return False, f"Source directory does not exist: {source}"

    def rollback(self, name: str, version: str | None = None) -> SimpleNamespace:
        """回滚 Skill 到指定版本。"""
        skill_dir = self.store_dir / name
        if not skill_dir.exists():
            raise StoreError(f"Skill '{name}' not installed")

        history = self.get_version_history(name)
        if not history:
            raise StoreError(f"No version history for '{name}'")

        snapshot_entries = [e for e in history if "snapshot" in e]
        if version:
            target_entry = None
            for entry in reversed(snapshot_entries):
                if entry["version"] == version:
                    target_entry = entry
                    break
            if not target_entry:
                raise StoreError(f"Version '{version}' not found in history")
        else:
            if len(snapshot_entries) < 1:
                raise StoreError(f"No previous version to rollback for '{name}'")
            target_entry = snapshot_entries[-1]

        snapshot_name = target_entry["snapshot"]
        snapshot_dir = skill_dir / ".versions" / snapshot_name
        if not snapshot_dir.exists():
            raise StoreError(f"Snapshot '{snapshot_name}' not found")

        self._backup_current_version(name)

        for item in skill_dir.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        for item in snapshot_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, skill_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, skill_dir / item.name)

        ir = parse_skill_md(skill_dir / "SKILL.md")

        meta_path = skill_dir / ".skill_meta.json"
        source = ""
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                source = meta.get("source", "")
            except (json.JSONDecodeError, OSError):
                pass

        self._update_index(name, ir, source)
        self.sync_skill_to_agents(name)

        logger.info("已回滚 Skill: %s → v%s", name, ir.version)
        return self.get(name)
