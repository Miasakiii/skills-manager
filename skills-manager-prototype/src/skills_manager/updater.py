"""版本更新检查模块。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from urllib.request import Request, urlopen

from . import __version__
from .logging import get_logger

logger = get_logger(__name__)


def _parse_version(v: str) -> tuple:
    """将版本字符串解析为可比较的元组。"""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        logger.warning("Failed to parse version %r, fallback to (0,)", v)
        return (0,)


@dataclass
class UpdateInfo:
    latest_version: str
    current_version: str
    has_update: bool
    release_url: str
    release_notes: str = ""


def _fetch_json(url: str, timeout: int = 5) -> Optional[dict]:
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        logger.debug("Failed to fetch %s", url, exc_info=True)
        return None


def check_pypi(package: str = "skillfmt") -> Optional[UpdateInfo]:
    """检查 PyPI 上的最新版本。"""
    data = _fetch_json(f"https://pypi.org/pypi/{package}/json")
    if not data:
        return None

    latest = data["info"]["version"]
    current = __version__

    try:
        has_update = _parse_version(latest) > _parse_version(current)
    except Exception:
        has_update = latest != current

    return UpdateInfo(
        latest_version=latest,
        current_version=current,
        has_update=has_update,
        release_url=data["info"].get("project_urls", {}).get("Homepage", ""),
        release_notes=data["info"].get("summary", ""),
    )


def check_github(
    owner: str = "Miasakiii", repo: str = "skills-manager"
) -> Optional[UpdateInfo]:
    """检查 GitHub Releases 上的最新版本。"""
    data = _fetch_json(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
    if not data:
        return None

    tag = data["tag_name"]
    latest = tag.lstrip("v")
    current = __version__

    try:
        has_update = _parse_version(latest) > _parse_version(current)
    except Exception:
        has_update = latest != current

    return UpdateInfo(
        latest_version=latest,
        current_version=current,
        has_update=has_update,
        release_url=data.get("html_url", ""),
        release_notes=data.get("body", "")[:500] if data.get("body") else "",
    )


def check_update(
    package: str = "skillfmt",
    github_owner: str = "Miasakiii",
    github_repo: str = "skills-manager",
) -> Optional[UpdateInfo]:
    """综合检查：优先 GitHub，回退 PyPI。"""
    info = check_github(github_owner, github_repo)
    if info:
        return info
    return check_pypi(package)


def format_update_message(info: UpdateInfo) -> str:
    """格式化更新提示。"""
    return f"新版本可用: v{info.latest_version} (当前 v{info.current_version})"
