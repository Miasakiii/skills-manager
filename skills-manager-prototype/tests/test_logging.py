"""测试日志模块。"""

import json
import logging
import sys
from unittest.mock import patch
from pathlib import Path


from skills_manager.logging import (
    _JsonFormatter,
    _ColorFormatter,
    setup,
    get_logger,
    shutdown,
)


# ── _JsonFormatter ─────────────────────────────────────────


class TestJsonFormatter:
    def test_basic_format(self):
        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Hello world",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert data["level"] == "INFO"
        assert data["msg"] == "Hello world"
        assert "ts" in data
        assert "logger" in data

    def test_exception_info(self):
        formatter = _JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Something failed",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert "test error" in data.get("exc", "")

    def test_ascii_disabled(self):
        """中文消息不应被 ASCII 转义。"""
        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="你好世界",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "你好世界" in result


# ── _ColorFormatter ─────────────────────────────────────────


class TestColorFormatter:
    def test_colored_output(self):
        formatter = _ColorFormatter("%(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "ERROR" in result
        assert "Error occurred" in result
        # ANSI 颜色码应存在
        assert "\033[" in result


# ── setup ───────────────────────────────────────────────────


class TestSetup:
    def test_idempotent(self):
        """多次调用 setup 不应添加重复 handler。"""
        # 重置全局状态
        import skills_manager.logging as log_mod

        log_mod._initialized = False

        with patch.object(Path, "mkdir"):
            setup(level=logging.WARNING, json_file=False)
            handler_count = len(logging.getLogger("skills_manager").handlers)
            setup(level=logging.WARNING, json_file=False)
            handler_count_after = len(logging.getLogger("skills_manager").handlers)
            assert handler_count == handler_count_after

        # 清理
        log_mod._initialized = False
        logging.getLogger("skills_manager").handlers.clear()

    def test_creates_log_dir(self):
        import skills_manager.logging as log_mod

        log_mod._initialized = False

        import tempfile

        tmpdir = Path(tempfile.mkdtemp())
        log_dir = tmpdir / "logs"
        setup(log_dir=log_dir, json_file=True)
        assert log_dir.exists()
        assert (log_dir / "skills-manager.log").exists()

        # 释放句柄
        log_mod.shutdown()
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)

        # 清理全局状态
        log_mod._initialized = False
        logging.getLogger("skills_manager").handlers.clear()


# ── get_logger ──────────────────────────────────────────────


class TestGetLogger:
    def test_auto_initializes(self):
        import skills_manager.logging as log_mod

        log_mod._initialized = False

        logger = get_logger("skills_manager.test")
        assert log_mod._initialized is True
        assert logger.name == "skills_manager.test"

        # 清理
        log_mod._initialized = False
        logging.getLogger("skills_manager").handlers.clear()

    def test_strips_prefix(self):
        """get_logger 应返回 skills_manager. 前缀的 logger。"""
        logger = get_logger("skills_manager.store")
        assert logger.name == "skills_manager.store"

    def test_short_name(self):
        logger = get_logger("custom")
        assert logger.name == "skills_manager.custom"


# ── shutdown ────────────────────────────────────────────────


class TestShutdown:
    def test_no_crash(self):
        """shutdown 不应抛出异常。"""
        shutdown()  # 应该正常执行
