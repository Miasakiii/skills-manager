"""本地存储管理。

管理已安装的 Skills，维护本地索引。
"""

from .agent_sync import _AgentSync
from .category import _CategoryManager
from .core import StoreError, _StoreCore
from .history import _HistoryTracker
from .installer import _SkillInstaller
from .scanner import _Scanner

__all__ = ["Store", "StoreError"]


class Store(
    _StoreCore,
    _SkillInstaller,
    _Scanner,
    _AgentSync,
    _CategoryManager,
    _HistoryTracker,
):
    """本地 Skill 存储管理器。"""
