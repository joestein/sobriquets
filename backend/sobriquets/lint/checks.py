import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

logger = logging.getLogger(__name__)


@dataclass
class LintIssue:
    """A wiki quality issue."""

    severity: str  # "error", "warning", "info"
    check: str
    file_path: str
    message: str


@dataclass
class LintReport:
    """Collection of lint results."""

    issues: list[LintIssue] = field(default_factory=list)
    files_checked: int = 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


def check_orphan_pages(pages_path: Path) -> list[LintIssue]:
    """Find pages that are not referenced by any other page."""
    issues: list[LintIssue] = []
    all_pages: dict[str, str] = {}  # rel_path -> content
    all_refs: set[str] = set()

    for md_file in pages_path.rglob("*.md"):
        rel_path = str(md_file.relative_to(pages_path))
        try:
            content = md_file.read_text(encoding="utf-8")
            all_pages[rel_path] = content
        except Exception:
            continue

    # Collect all cross-references
    ref_pattern = re.compile(r"\[\[(?:pages/)?([^\]]+)\]\]")
    related_pattern = re.compile(r"^\s*-\s+(?:pages/)?(\S+\.md)", re.MULTILINE)

    for rel_path, content in all_pages.items():
        for match in ref_pattern.finditer(content):
            all_refs.add(match.group(1))
        for match in related_pattern.finditer(content):
            all_refs.add(match.group(1))

    # Check for orphans (skip _index.md files)
    for rel_path in all_pages:
        if Path(rel_path).name == "_index.md":
            continue
        if rel_path not in all_refs:
            issues.append(
                LintIssue(
                    severity="warning",
                    check="orphan_page",
                    file_path=rel_path,
                    message="Page is not referenced by any other page",
                )
            )

    return issues


def check_missing_frontmatter(pages_path: Path) -> list[LintIssue]:
    """Check for pages missing required frontmatter fields."""
    issues: list[LintIssue] = []
    required_fields = ["title", "topic"]

    for md_file in pages_path.rglob("*.md"):
        rel_path = str(md_file.relative_to(pages_path))
        try:
            post = frontmatter.load(str(md_file))
        except Exception as e:
            issues.append(
                LintIssue(
                    severity="error",
                    check="frontmatter_parse",
                    file_path=rel_path,
                    message=f"Failed to parse frontmatter: {e}",
                )
            )
            continue

        for field_name in required_fields:
            if field_name not in post.metadata:
                issues.append(
                    LintIssue(
                        severity="error",
                        check="missing_frontmatter",
                        file_path=rel_path,
                        message=f"Missing required frontmatter field: {field_name}",
                    )
                )

    return issues


def check_broken_cross_refs(pages_path: Path) -> list[LintIssue]:
    """Check for cross-references pointing to non-existent pages."""
    issues: list[LintIssue] = []
    ref_pattern = re.compile(r"\[\[(?:pages/)?([^\]]+)\]\]")

    for md_file in pages_path.rglob("*.md"):
        rel_path = str(md_file.relative_to(pages_path))
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in ref_pattern.finditer(content):
            ref_path = match.group(1)
            target = pages_path / ref_path
            if not target.exists():
                issues.append(
                    LintIssue(
                        severity="error",
                        check="broken_cross_ref",
                        file_path=rel_path,
                        message=f"Cross-reference target does not exist: {ref_path}",
                    )
                )

    return issues


def check_stale_sources(
    pages_path: Path, raw_sources_path: Path
) -> list[LintIssue]:
    """Check for source references pointing to non-existent raw source files."""
    issues: list[LintIssue] = []
    source_pattern = re.compile(r"raw-sources/([^\s\])\">]+)")

    for md_file in pages_path.rglob("*.md"):
        rel_path = str(md_file.relative_to(pages_path))
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in source_pattern.finditer(content):
            source_ref = match.group(1)
            # Resolve relative to wiki root (parent of pages_path)
            wiki_root = pages_path.parent
            target = wiki_root / "raw-sources" / source_ref
            if not target.exists():
                issues.append(
                    LintIssue(
                        severity="warning",
                        check="stale_source",
                        file_path=rel_path,
                        message=f"Referenced raw source does not exist: raw-sources/{source_ref}",
                    )
                )

    return issues


def run_all_checks(pages_path: Path, raw_sources_path: Path) -> LintReport:
    """Run all lint checks and return a report."""
    report = LintReport()

    md_files = list(pages_path.rglob("*.md"))
    report.files_checked = len(md_files)

    report.issues.extend(check_missing_frontmatter(pages_path))
    report.issues.extend(check_orphan_pages(pages_path))
    report.issues.extend(check_broken_cross_refs(pages_path))
    report.issues.extend(check_stale_sources(pages_path, raw_sources_path))

    return report
