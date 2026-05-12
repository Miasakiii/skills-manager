"""测试版本更新检查模块。"""

import json
from unittest.mock import patch, MagicMock
from urllib.error import URLError

import pytest

from skills_manager import __version__
from skills_manager.updater import (
    _parse_version,
    UpdateInfo,
    _fetch_json,
    check_pypi,
    check_github,
    check_update,
    format_update_message,
)


# ── _parse_version ──────────────────────────────────────────


class TestParseVersion:
    def test_simple_version(self):
        assert _parse_version("1.0.0") == (1, 0, 0)

    def test_two_part(self):
        assert _parse_version("1.2") == (1, 2)

    def test_with_whitespace(self):
        assert _parse_version("  1.0.0  ") == (1, 0, 0)

    def test_invalid_returns_zero(self):
        assert _parse_version("abc") == (0,)

    def test_comparison(self):
        assert _parse_version("1.2.0") > _parse_version("1.1.0")
        assert _parse_version("2.0.0") > _parse_version("1.9.9")


# ── _fetch_json ─────────────────────────────────────────────


class TestFetchJson:
    def test_success(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"key": "value"}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("skills_manager.updater.urlopen", return_value=mock_response):
            result = _fetch_json("https://example.com")
            assert result == {"key": "value"}

    def test_failure_returns_none(self):
        with patch("skills_manager.updater.urlopen", side_effect=URLError("timeout")):
            result = _fetch_json("https://example.com")
            assert result is None


# ── check_pypi ──────────────────────────────────────────────


class TestCheckPyPI:
    def test_update_available(self):
        mock_data = {
            "info": {
                "version": "9.9.9",
                "project_urls": {"Homepage": "https://example.com"},
                "summary": "A great package",
            }
        }
        with patch("skills_manager.updater._fetch_json", return_value=mock_data):
            info = check_pypi()
            assert info is not None
            assert info.latest_version == "9.9.9"
            assert info.has_update is True
            assert info.release_url == "https://example.com"

    def test_up_to_date(self):
        mock_data = {
            "info": {
                "version": __version__,
                "project_urls": {},
                "summary": "",
            }
        }
        with patch("skills_manager.updater._fetch_json", return_value=mock_data):
            info = check_pypi()
            assert info is not None
            assert info.has_update is False
            assert info.current_version == __version__

    def test_network_failure(self):
        with patch("skills_manager.updater._fetch_json", return_value=None):
            info = check_pypi()
            assert info is None


# ── check_github ────────────────────────────────────────────


class TestCheckGithub:
    def test_update_available(self):
        mock_data = {
            "tag_name": "v9.9.9",
            "html_url": "https://github.com/owner/repo/releases/tag/v9.9.9",
            "body": "New features",
        }
        with patch("skills_manager.updater._fetch_json", return_value=mock_data):
            info = check_github()
            assert info is not None
            assert info.latest_version == "9.9.9"
            assert info.has_update is True
            assert "New features" in info.release_notes

    def test_up_to_date(self):
        mock_data = {
            "tag_name": f"v{__version__}",
            "html_url": "https://example.com",
            "body": None,
        }
        with patch("skills_manager.updater._fetch_json", return_value=mock_data):
            info = check_github()
            assert info is not None
            assert info.has_update is False

    def test_network_failure(self):
        with patch("skills_manager.updater._fetch_json", return_value=None):
            info = check_github()
            assert info is None


# ── check_update (composite) ────────────────────────────────


class TestCheckUpdate:
    def test_github_first(self):
        """优先返回 GitHub 结果。"""
        github_data = {"tag_name": "v9.9.9", "html_url": "https://gh.com", "body": ""}
        with patch("skills_manager.updater._fetch_json", return_value=github_data):
            info = check_update()
            assert info is not None
            assert info.latest_version == "9.9.9"

    def test_fallback_to_pypi(self):
        """GitHub 失败时回退到 PyPI。"""
        pypi_data = {
            "info": {
                "version": "9.9.9",
                "project_urls": {},
                "summary": "",
            }
        }
        call_count = 0

        def mock_fetch(url, timeout=5):
            nonlocal call_count
            call_count += 1
            if "github" in url:
                return None  # GitHub 失败
            return pypi_data  # PyPI 成功

        with patch("skills_manager.updater._fetch_json", side_effect=mock_fetch):
            info = check_update()
            assert info is not None
            assert info.latest_version == "9.9.9"
            assert call_count >= 2  # 至少调了两次

    def test_both_fail(self):
        with patch("skills_manager.updater._fetch_json", return_value=None):
            info = check_update()
            assert info is None


# ── format_update_message ───────────────────────────────────


class TestFormatUpdateMessage:
    def test_formats_correctly(self):
        info = UpdateInfo(
            latest_version="1.2.0",
            current_version="1.1.0",
            has_update=True,
            release_url="https://example.com",
        )
        msg = format_update_message(info)
        assert "v1.2.0" in msg
        assert "v1.1.0" in msg
