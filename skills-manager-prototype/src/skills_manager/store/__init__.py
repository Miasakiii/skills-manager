"""本地存储管理。

管理已安装的 Skills，维护本地索引。
"""

from .agent_sync import _AgentSync
from .category import _CategoryManager
from .core import StoreError, _StoreCore
from .history import _HistoryTracker
from .installer import _SkillInstaller
from .profile import _ProfileManager
from .scanner import _Scanner
from .translation import _TranslationManager

__all__ = ["Store", "StoreError"]


class Store(
    _StoreCore,
    _SkillInstaller,
    _Scanner,
    _AgentSync,
    _CategoryManager,
    _TranslationManager,
    _ProfileManager,
    _HistoryTracker,
):
    """本地 Skill 存储管理器。"""
