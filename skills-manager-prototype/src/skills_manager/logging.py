"""结构化日志系统。

使用 Python 标准 logging 模块，支持：
- 控制台输出（带颜色）
- JSON 结构化文件输出
- 日志级别按模块配置
- 自动轮转
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path

# 默认日志目录
_DEFAULT_LOG_DIR = Path.home() / ".skills-manager" / "logs"


class _JsonFormatter(logging.Formatter):
    """JSON 结构化日志格式化器。"""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["exc"] = str(record.exc_info[1])
        return json.dumps(entry, ensure_ascii=False)


class _ColorFormatter(logging.Formatter):
    """带颜色的控制台格式化器。"""

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[35m",  # magenta
    }
    RESET = "\033[0m"
    GREY = "\033[90m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        msg = super().format(record)
        return f"{self.GREY}{ts}{self.RESET} {color}{record.levelname:<7}{self.RESET} {record.name}  {msg}"


# 全局状态
_initialized = False


def setup(
    log_dir: Path | None = None,
    level: int = logging.INFO,
    json_file: bool = True,
) -> None:
    """初始化日志系统（幂等，只在首次调用时生效）。

    Args:
        log_dir: 日志文件目录，默认 ~/.skills-manager/logs/
        level: 根日志级别
        json_file: 是否启用 JSON 文件日志
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    root = logging.getLogger("skills_manager")
    root.setLevel(level)

    # 控制台处理器
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(_ColorFormatter("%(message)s"))
    root.addHandler(console)

    # 文件处理器（JSON）
    if json_file:
        log_dir = Path(log_dir or _DEFAULT_LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "skills-manager.log",
            maxBytes=1_000_000,  # 1 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_JsonFormatter())
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器。

    Args:
        name: 通常传 __name__ 即可，会自动去掉 skills_manager 前缀（如 skills_manager.store → store）。
    """
    # 自动初始化
    if not _initialized:
        setup()

    short = name
    if short.startswith("skills_manager."):
        short = short[len("skills_manager."):]
    elif short == "skills_manager":
        short = "root"
    return logging.getLogger(f"skills_manager.{short}")


def shutdown() -> None:
    """清理日志处理器。"""
    logging.shutdown()
