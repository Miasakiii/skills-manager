"""Profile 管理。"""

from __future__ import annotations

from datetime import datetime, timezone

from ..logging import get_logger
from .core import StoreError

logger = get_logger(__name__)


class _ProfileManager:
    """Profile 管理 mixin。"""

    def get_profiles(self) -> list[dict]:
        """获取所有 Profile。"""
        return self._read_json(self.base_dir / "profiles.json", [])

    def _save_profiles(self, profiles: list[dict]) -> None:
        """保存 Profile 列表。"""
        self._write_json(self.base_dir / "profiles.json", profiles)

    def create_profile(
        self,
        name: str,
        description: str = "",
        skills: list[str] | None = None,
    ) -> dict:
        """创建 Profile。"""
        profiles = self.get_profiles()

        for p in profiles:
            if p["name"] == name:
                raise StoreError(f"Profile '{name}' already exists")

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
        """更新 Profile。"""
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

        raise StoreError(f"Profile '{name}' not found")

    def delete_profile(self, name: str) -> None:
        """删除 Profile。"""
        profiles = self.get_profiles()
        profiles = [p for p in profiles if p["name"] != name]
        self._save_profiles(profiles)

    def get_profile(self, name: str) -> dict:
        """获取单个 Profile。"""
        profiles = self.get_profiles()
        for p in profiles:
            if p["name"] == name:
                return p
        raise StoreError(f"Profile '{name}' not found")

    def add_skill_to_profile(self, profile_name: str, skill_name: str) -> None:
        """向 Profile 添加 Skill。"""
        profiles = self.get_profiles()
        for p in profiles:
            if p["name"] == profile_name:
                if skill_name not in p["skills"]:
                    p["skills"].append(skill_name)
                    p["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._save_profiles(profiles)
                return
        raise StoreError(f"Profile '{profile_name}' not found")

    def remove_skill_from_profile(self, profile_name: str, skill_name: str) -> None:
        """从 Profile 移除 Skill。"""
        profiles = self.get_profiles()
        for p in profiles:
            if p["name"] == profile_name:
                if skill_name in p["skills"]:
                    p["skills"].remove(skill_name)
                    p["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._save_profiles(profiles)
                return
        raise StoreError(f"Profile '{profile_name}' not found")
