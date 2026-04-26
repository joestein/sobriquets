import logging
import sys
from pathlib import Path

from sobriquets.config import get_settings
from sobriquets.lint.checks import run_all_checks


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    settings = get_settings()
    pages_path = Path(settings.WIKI_PAGES_PATH)
    raw_sources_path = Path(settings.WIKI_RAW_SOURCES_PATH)

    if not pages_path.exists():
        print(f"Wiki pages path does not exist: {pages_path}")
        sys.exit(1)

    report = run_all_checks(pages_path, raw_sources_path)

    print(f"\n--- Wiki Lint Report ---")
    print(f"  Files checked: {report.files_checked}")
    print(f"  Errors:        {report.error_count}")
    print(f"  Warnings:      {report.warning_count}")
    print()

    if not report.issues:
        print("  No issues found.")
        return

    for issue in sorted(report.issues, key=lambda i: (i.severity, i.file_path)):
        severity_marker = {
            "error": "ERROR",
            "warning": "WARN ",
            "info": "INFO ",
        }.get(issue.severity, "?????")
        print(f"  [{severity_marker}] {issue.file_path}: {issue.message}")

    if report.error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
