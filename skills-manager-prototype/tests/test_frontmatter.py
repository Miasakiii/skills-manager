"""测试 frontmatter 分割工具。"""

import pytest

from skills_manager.frontmatter import FrontmatterError, split_frontmatter


class TestSplitFrontmatter:
    def test_basic(self):
        content = "---\nname: test\n---\n# Body\n"
        fm, body = split_frontmatter(content)
        assert fm == "name: test"
        assert body == "# Body"

    def test_no_frontmatter(self):
        content = "# No frontmatter\n"
        fm, body = split_frontmatter(content)
        assert fm == ""
        assert body == "# No frontmatter\n"

    def test_unclosed_frontmatter(self):
        content = "---\nname: test\n"
        with pytest.raises(FrontmatterError, match="未闭合"):
            split_frontmatter(content)

    def test_bom(self):
        content = "﻿---\nname: test\n---\nbody"
        fm, body = split_frontmatter(content)
        assert fm == "name: test"
        assert body == "body"

    def test_empty_frontmatter(self):
        content = "---\n---\nbody"
        fm, body = split_frontmatter(content)
        assert fm == ""
        assert body == "body"

    def test_multiline_body(self):
        content = "---\nname: test\n---\n# Title\n\nParagraph\n"
        fm, body = split_frontmatter(content)
        assert fm == "name: test"
        assert "# Title" in body
