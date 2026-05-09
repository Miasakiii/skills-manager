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
            # 备份当前版本（如果存在且 force=True）
            if force:
                self._backup_current_version(install_name)
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

        # 记录版本历史
        history = self.get_version_history(install_name)
        history.append({
            "version": ir.version,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "description": ir.description,
        })
        self._save_version_history(install_name, history)

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

    def install_from_url(self, url: str) -> SimpleNamespace:
        """从 URL 安装 Skill。

        支持：
        - 直接 .skill 包文件 URL
        - GitHub 仓库 URL（自动下载 zip）

        Args:
            url: URL 地址。

        Returns:
            安装后的 Skill 信息。
        """
        try:
            import httpx
        except ImportError:
            raise StoreError(
                "需要安装 httpx：pip install skills-manager[remote]"
            )

        tmp_dir = self.base_dir / ".tmp"
        tmp_dir.mkdir(exist_ok=True)

        try:
            # 判断是否为 GitHub 仓库 URL
            if "github.com" in url and not url.endswith((".skill", ".tar.gz", ".zip")):
                return self._install_from_github(url, tmp_dir)

            # 直接下载文件
            return self._install_from_file_url(url, tmp_dir)
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)

    def _install_from_file_url(
        self, url: str, tmp_dir: Path
    ) -> SimpleNamespace:
        """从文件 URL 安装。"""
        import httpx

        # 下载文件
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()

        # 保存到临时文件
        file_name = url.split("/")[-1] or "download"
        file_path = tmp_dir / file_name
        file_path.write_bytes(response.content)

        # 如果是 .skill 包，直接安装
        if file_name.endswith(".skill"):
            return self.install_from_package(file_path)

        # 如果是压缩包，解压后查找 SKILL.md
        if file_name.endswith((".tar.gz", ".tgz", ".zip")):
            return self._install_from_archive(file_path, tmp_dir)

        raise StoreError(f"不支持的文件格式: {file_name}")

    def _install_from_github(
        self, url: str, tmp_dir: Path
    ) -> SimpleNamespace:
        """从 GitHub 仓库安装。"""
        import httpx

        # 解析 GitHub URL
        # 支持: https://github.com/user/repo
        # 支持: https://github.com/user/repo/tree/branch/path
        parts = url.replace("https://github.com/", "").strip("/").split("/")
        if len(parts) < 2:
            raise StoreError(f"无效的 GitHub URL: {url}")

        user, repo = parts[0], parts[1]
        branch = "main"
        sub_path = ""

        if len(parts) > 3 and parts[2] == "tree":
            branch = parts[3] if len(parts) > 3 else "main"
            sub_path = "/".join(parts[4:]) if len(parts) > 4 else ""

        # 下载 zip
        zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"
        response = httpx.get(zip_url, follow_redirects=True, timeout=30)
        response.raise_for_status()

        zip_path = tmp_dir / "repo.zip"
        zip_path.write_bytes(response.content)

        # 解压
        import zipfile
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)

        # 查找 SKILL.md
        extracted_dir = tmp_dir / f"{repo}-{branch}"
        if sub_path:
            search_dir = extracted_dir / sub_path
        else:
            search_dir = extracted_dir

        skill_dir = self._find_skill_dir(search_dir)
        if not skill_dir:
            raise StoreError("GitHub 仓库中未找到 SKILL.md")

        return self.install(skill_dir)

    def _install_from_archive(
        self, archive_path: Path, tmp_dir: Path
    ) -> SimpleNamespace:
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
                tf.extractall(extract_dir)

        skill_dir = self._find_skill_dir(extract_dir)
        if not skill_dir:
            raise StoreError("压缩包中未找到 SKILL.md")

        return self.install(skill_dir)

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

    def scan_directory_with_info(self, root: Path) -> list[dict]:
        """扫描目录，返回每个 Skill 的详细信息。

        Returns:
            列表，每项包含 path, name, version, description, installed。
        """
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

    # ── 导出历史 ──────────────────────────────────────────────

    def get_export_history(self) -> list[dict]:
        """获取导出历史记录。

        Returns:
            导出历史列表，每个元素包含：
            - skill_name: Skill 名称
            - format: 导出格式
            - output_path: 输出路径
            - exported_at: 导出时间
        """
        history_path = self.base_dir / "export_history.json"
        if history_path.exists():
            try:
                return json.loads(history_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def add_export_history(
        self,
        skill_name: str,
        format_name: str,
        output_path: str,
    ) -> None:
        """添加导出历史记录。

        Args:
            skill_name: Skill 名称。
            format_name: 导出格式。
            output_path: 输出路径。
        """
        history = self.get_export_history()
        history.append({
            "skill_name": skill_name,
            "format": format_name,
            "output_path": output_path,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        })
        # 只保留最近 100 条记录
        if len(history) > 100:
            history = history[-100:]
        history_path = self.base_dir / "export_history.json"
        history_path.write_text(
            json.dumps(history, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def clear_export_history(self) -> None:
        """清空导出历史记录。"""
        history_path = self.base_dir / "export_history.json"
        if history_path.exists():
            history_path.unlink()

    # ── Profile 管理 ──────────────────────────────────────────

    def get_profiles(self) -> list[dict]:
        """获取所有 Profile。

        Returns:
            Profile 列表，每个元素包含：
            - name: Profile 名称
            - description: 描述
            - skills: 包含的 Skill 名称列表
            - created_at: 创建时间
            - updated_at: 更新时间
        """
        profiles_path = self.base_dir / "profiles.json"
        if profiles_path.exists():
            try:
                return json.loads(profiles_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_profiles(self, profiles: list[dict]) -> None:
        """保存 Profile 列表。"""
        profiles_path = self.base_dir / "profiles.json"
        profiles_path.write_text(
            json.dumps(profiles, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def create_profile(
        self,
        name: str,
        description: str = "",
        skills: list[str] | None = None,
    ) -> dict:
        """创建 Profile。

        Args:
            name: Profile 名称。
            description: 描述。
            skills: 包含的 Skill 名称列表。

        Returns:
            创建的 Profile 信息。
        """
        profiles = self.get_profiles()

        # 检查名称是否已存在
        for p in profiles:
            if p["name"] == name:
                raise StoreError(f"Profile '{name}' 已存在")

        now = datetime.now(timezone.utc).isoformat()
        profile = {
            "name": name,
            "description": description,
            "skills": skills or [],
            "created_at": now,
            "updated_at": now,
        }
        profiles.append(profile)
        self._save_profiles(profiles)
        return profile

    def update_profile(
        self,
        name: str,
        description: str | None = None,
        skills: list[str] | None = None,
    ) -> dict:
        """更新 Profile。

        Args:
            name: Profile 名称。
            description: 新描述（None 则不更新）。
            skills: 新的 Skill 列表（None 则不更新）。

        Returns:
            更新后的 Profile 信息。
        """
        profiles = self.get_profiles()

        for p in profiles:
            if p["name"] == name:
                if description is not None:
                    p["description"] = description
                if skills is not None:
                    p["skills"] = skills
                p["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_profiles(profiles)
                return p

        raise StoreError(f"Profile '{name}' 不存在")

    def delete_profile(self, name: str) -> None:
        """删除 Profile。

        Args:
            name: Profile 名称。
        """
        profiles = self.get_profiles()
        profiles = [p for p in profiles if p["name"] != name]
        self._save_profiles(profiles)

    def get_profile(self, name: str) -> dict:
        """获取单个 Profile。

        Args:
            name: Profile 名称。

        Returns:
            Profile 信息。
        """
        profiles = self.get_profiles()
        for p in profiles:
            if p["name"] == name:
                return p
        raise StoreError(f"Profile '{name}' 不存在")

    def add_skill_to_profile(self, profile_name: str, skill_name: str) -> None:
        """向 Profile 添加 Skill。

        Args:
            profile_name: Profile 名称。
            skill_name: Skill 名称。
        """
        profiles = self.get_profiles()
        for p in profiles:
            if p["name"] == profile_name:
                if skill_name not in p["skills"]:
                    p["skills"].append(skill_name)
                    p["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._save_profiles(profiles)
                return
        raise StoreError(f"Profile '{profile_name}' 不存在")

    def remove_skill_from_profile(self, profile_name: str, skill_name: str) -> None:
        """从 Profile 移除 Skill。

        Args:
            profile_name: Profile 名称。
            skill_name: Skill 名称。
        """
        profiles = self.get_profiles()
        for p in profiles:
            if p["name"] == profile_name:
                if skill_name in p["skills"]:
                    p["skills"].remove(skill_name)
                    p["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._save_profiles(profiles)
                return
        raise StoreError(f"Profile '{profile_name}' 不存在")

    # ── 版本管理 ──────────────────────────────────────────────

    def get_version_history(self, name: str) -> list[dict]:
        """获取 Skill 的版本历史。

        Args:
            name: Skill 名称。

        Returns:
            版本历史列表，每个元素包含 version, installed_at, source 信息。
        """
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

        # 读取当前版本信息
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return

        ir = parse_skill_md(skill_md)
        versions_dir = skill_dir / ".versions"
        versions_dir.mkdir(exist_ok=True)

        # 创建版本快照目录
        version_name = ir.version.replace(".", "_")
        snapshot_dir = versions_dir / f"v{version_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        snapshot_dir.mkdir(exist_ok=True)

        # 复制当前文件到快照（排除版本元数据）
        for item in skill_dir.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_file():
                shutil.copy2(item, snapshot_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, snapshot_dir / item.name)

        # 记录版本历史
        history = self.get_version_history(name)
        history.append({
            "version": ir.version,
            "snapshot": snapshot_dir.name,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "description": ir.description,
        })
        self._save_version_history(name, history)

    def upgrade(self, name: str, source: Path) -> SimpleNamespace:
        """升级 Skill 到新版本。

        Args:
            name: Skill 名称。
            source: 新版本的 Skill 目录路径。

        Returns:
            升级后的 Skill 信息。
        """
        if not (self.store_dir / name).exists():
            raise StoreError(f"Skill '{name}' not installed")

        # 验证新版本
        validation = validate_skill_dir(source)
        if not validation.valid:
            raise StoreError(f"验证失败: {'; '.join(validation.errors)}")

        # 解析新版本
        new_ir = parse_skill_md(source / "SKILL.md")

        # 备份当前版本（会在内部保存版本历史）
        self._backup_current_version(name)

        # 读取当前版本历史（备份后，删除前）
        history = self.get_version_history(name)

        # 安装新版本（保留 .versions 目录）
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

        # 恢复 .versions 目录
        if versions_tmp.exists():
            shutil.move(str(versions_tmp), str(versions_dir))

        # 写入安装元数据
        meta = {
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "upgraded": True,
        }
        (target / ".skill_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # 记录新版本到历史
        history.append({
            "version": new_ir.version,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(source),
            "description": new_ir.description,
        })
        self._save_version_history(name, history)

        # 更新索引
        self._update_index(name, new_ir, str(source))

        # 同步到 agent 目录
        self.sync_skill_to_agents(name)

        return self.get(name)

    def update(self, name: str) -> SimpleNamespace:
        """从原始来源重新安装最新版本。

        Args:
            name: Skill 名称。

        Returns:
            更新后的 Skill 信息。
        """
        skill_info = self.get(name)
        source = getattr(skill_info, "source", "")

        if not source:
            raise StoreError(f"Skill '{name}' 没有来源信息，无法更新")

        # 判断来源类型
        if source.startswith(("http://", "https://", "github:")):
            # URL 来源：重新下载安装
            return self.install_from_url(source)

        # 本地目录来源
        source_path = Path(source)
        if not source_path.exists():
            raise StoreError(f"来源目录不存在: {source}")

        return self.upgrade(name, source_path)

    def can_update(self, name: str) -> tuple[bool, str]:
        """检查 Skill 是否可以更新。

        Returns:
            (是否可更新, 原因说明)
        """
        try:
            skill_info = self.get(name)
        except StoreError:
            return False, "Skill 不存在"

        source = getattr(skill_info, "source", "")
        if not source:
            return False, "没有来源信息"

        if source.startswith(("http://", "https://", "github:")):
            return True, f"来源: {source}"

        source_path = Path(source)
        if source_path.exists():
            return True, f"来源: {source_path}"
        return False, f"来源目录不存在: {source}"

    def rollback(self, name: str, version: str | None = None) -> SimpleNamespace:
        """回滚 Skill 到指定版本。

        Args:
            name: Skill 名称。
            version: 要回滚的版本号，None 则回滚到上一个版本。

        Returns:
            回滚后的 Skill 信息。
        """
        skill_dir = self.store_dir / name
        if not skill_dir.exists():
            raise StoreError(f"Skill '{name}' not installed")

        # 获取版本历史
        history = self.get_version_history(name)
        if not history:
            raise StoreError(f"No version history for '{name}'")

        # 找到目标版本（只查找有快照的条目）
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
            # 回滚到上一个版本
            if len(snapshot_entries) < 1:
                raise StoreError(f"No previous version to rollback for '{name}'")
            target_entry = snapshot_entries[-1]

        # 查找快照目录
        snapshot_name = target_entry["snapshot"]
        snapshot_dir = skill_dir / ".versions" / snapshot_name
        if not snapshot_dir.exists():
            raise StoreError(f"Snapshot '{snapshot_name}' not found")

        # 备份当前版本（回滚前）
        self._backup_current_version(name)

        # 恢复快照
        # 删除当前文件（排除版本元数据）
        for item in skill_dir.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        # 复制快照文件
        for item in snapshot_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, skill_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, skill_dir / item.name)

        # 解析恢复的版本
        ir = parse_skill_md(skill_dir / "SKILL.md")

        # 更新索引
        meta_path = skill_dir / ".skill_meta.json"
        source = ""
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                source = meta.get("source", "")
            except (json.JSONDecodeError, OSError):
                pass

        self._update_index(name, ir, source)

        # 同步到 agent 目录
        self.sync_skill_to_agents(name)

        return self.get(name)
