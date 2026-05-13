"""Claude Code 兼容性检查。

扫描 .claude/skills/ 目录，诊断 SKILL.md 的格式问题，
并自动修复简单问题（缺少 name、name 不匹配等）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .security import sanitize_name


@dataclass
class SkillIssue:
    """一个兼容性问题。"""
    severity: str       # "error" | "warning"
    message: str
    auto_fixable: bool = False


@dataclass
class SkillReport:
    """单个 skill 的检查报告。"""
    path: Path
    name: str = ""
    issues: list[SkillIssue] = field(default_factory=list)
    fixed: bool = False

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


class ClaudeCodeChecker:
    """Claude Code skills 目录兼容性检查器。"""

    # 必需的 frontmatter 字段
    REQUIRED_FIELDS = ["name", "description"]

    def __init__(self, skills_dir: Path | None = None):
        self.skills_dir = skills_dir or Path.home() / ".claude" / "skills"

    def scan(self) -> list[SkillReport]:
        """扫描所有 skill 目录，返回诊断报告列表。"""
        reports: list[SkillReport] = []
        if not self.skills_dir.is_dir():
            return reports

        for item in sorted(self.skills_dir.iterdir()):
            if not item.is_dir() or item.name.startswith("."):
                continue
            report = self._check_one(item)
            reports.append(report)

        return reports

    def _check_one(self, skill_dir: Path) -> SkillReport:
        """检查单个 skill 目录。"""
        report = SkillReport(path=skill_dir, name=skill_dir.name)
        md_path = skill_dir / "SKILL.md"

        if not md_path.exists():
            report.issues.append(SkillIssue(
                severity="error",
                message="缺少 SKILL.md 文件",
            ))
            return report

        try:
            content = md_path.read_text(encoding="utf-8")
        except OSError as e:
            report.issues.append(SkillIssue(
                severity="error",
                message=f"无法读取 SKILL.md: {e}",
            ))
            return report

        fm = self._parse_frontmatter(content)

        # 检查必需的 frontmatter 字段
        for field in self.REQUIRED_FIELDS:
            if not fm.get(field):
                report.issues.append(SkillIssue(
                    severity="error",
                    message=f"frontmatter 缺少 {field} 字段",
                    auto_fixable=True if field == "name" else False,
                ))

        # 检查 name 是否匹配目录名
        fm_name = fm.get("name", "")
        if fm_name and fm_name != skill_dir.name:
            report.issues.append(SkillIssue(
                severity="warning",
                message=f"name '{fm_name}' 与目录名 '{skill_dir.name}' 不匹配",
                auto_fixable=True,
            ))

        # 检查 description 是否为空
        desc = fm.get("description", "")
        if desc and desc.strip() in ("", '""', "''"):
            report.issues.append(SkillIssue(
                severity="warning",
                message="description 为空",
            ))

        return report

    @staticmethod
    def _parse_frontmatter(content: str) -> dict[str, str]:
        """解析 YAML frontmatter，返回字段字典。"""
        from .frontmatter import split_frontmatter

        try:
            frontmatter, _ = split_frontmatter(content)
        except Exception:
            return {}
        if not frontmatter:
            return {}
        result: dict[str, str] = {}
        for line in frontmatter.split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
        return result

    def auto_fix(self, reports: list[SkillReport]) -> int:
        """自动修复可修复的问题，返回修复数量。"""
        fixed_count = 0
        for report in reports:
            if self._fix_one(report):
                fixed_count += 1
        return fixed_count

    def _fix_one(self, report: SkillReport) -> bool:
        """尝试修复单个 skill 的问题。"""
        if not report.issues:
            return False

        md_path = report.path / "SKILL.md"
        if not md_path.exists():
            return False

        try:
            content = md_path.read_text(encoding="utf-8")
        except OSError:
            return False

        safe_name = sanitize_name(report.name)

        has_frontmatter = content.startswith("---")
        fixed = False

        if has_frontmatter:
            fm_match = re.match(r'^(---\s*\n)(.*?)(\n---)', content, re.DOTALL)
            if fm_match:
                prefix = fm_match.group(1)
                fm_body = fm_match.group(2)
                suffix = fm_match.group(3) + content[fm_match.end():]
                fm = self._parse_frontmatter(content)
                fm_name = fm.get("name", "")

                if not fm_name:
                    fm_body = f"name: {safe_name}\n{fm_body}"
                    fixed = True
                elif fm_name != report.name:
                    fm_body = re.sub(
                        r'^name:\s*["\']?.*?["\']?\s*$',
                        f"name: {safe_name}",
                        fm_body,
                        count=1,
                        flags=re.MULTILINE,
                    )
                    fixed = True

                if fixed:
                    content = prefix + fm_body + suffix
        else:
            content = f'---\nname: {safe_name}\ndescription: "{safe_name} skill"\n---\n\n{content}'
            fixed = True

        if fixed:
            md_path.write_text(content, encoding="utf-8")
            report.fixed = True

        return fixed

    def summary(self, reports: list[SkillReport]) -> str:
        """生成扫描结果摘要。"""
        total = len(reports)
        ok = sum(1 for r in reports if r.ok)
        errors = sum(r.error_count for r in reports)
        warnings = sum(r.warning_count for r in reports)
        lines = [
            f"扫描 {total} 个 skills",
            f"  {ok} 个正常",
            f"  {errors} 个错误",
            f"  {warnings} 个警告",
        ]
        if errors or warnings:
            lines.append("")
            lines.append("有问题 skills:")
            for r in reports:
                if r.issues:
                    lines.append(f"  {r.name}:")
                    for issue in r.issues:
                        fixable = " [可自动修复]" if issue.auto_fixable else ""
                        lines.append(f"    [{issue.severity}] {issue.message}{fixable}")
        return "\n".join(lines)
