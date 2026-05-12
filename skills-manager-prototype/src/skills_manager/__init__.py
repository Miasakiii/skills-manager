"""Skills Manager - AI Skill 格式转换与管理工具"""

try:
    from importlib.metadata import version

    __version__ = version("skillfmt")
except Exception:
    __version__ = "0.0.0+dev"
