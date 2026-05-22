"""Quality checks for cleaned Markdown books."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .frontmatter import find_isbns_in_text, read_frontmatter_and_body


CLEAN_CHECK_VERSION = "0.1.0"


IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)(?:\{[^}]*\})?")
HTML_TAG_RE = re.compile(r"</?[a-zA-Z][a-zA-Z0-9:-]*(?:\s+[^<>]*)?>")
SVG_RE = re.compile(r"<svg\b|</svg>|<image\b|</image>", re.IGNORECASE)
PANDOC_SPAN_RE = re.compile(r"\[[^\]]+\]\{[^}]*\}")
EMPTY_ANCHOR_RE = re.compile(r"\[\]\{#[^}]+\}")
PANDOC_DIV_FENCE_RE = re.compile(r"^\s*:{3,}.*$", re.MULTILINE)
PANDOC_ATTRIBUTE_RE = re.compile(r"\{[#.][^}]+\}")
RAW_HTML_FENCE_RE = re.compile(r"`<[^`]+>`\{=html\}")
EPUB_ID_RE = re.compile(r"(xhtml|_idGen|CharOverride|NoBreak|ObjectStyle|TextAnchor|idContainer)")
FOOTNOTE_BACKLINK_RE = re.compile(r"#.*footnote.*backlink|_idFootnoteLink|_idFootnotes")
NBSP_RE = re.compile(r"\u00a0")
HARD_WRAP_SPLIT_RE = re.compile(r"[a-z]\n[a-z]")
BROKEN_WORD_RE = re.compile(r"\b[a-zA-Z]{1,4}\[\s*\n?[a-zA-Z]{1,20}\]?")
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


STATUS_OK = "OK"
STATUS_WARN = "WARN"
STATUS_FAIL = "FAIL"


def status_for_count(count: int, warn_at: int = 1, fail_at: int = 10) -> str:
    if count >= fail_at:
        return STATUS_FAIL
    if count >= warn_at:
        return STATUS_WARN
    return STATUS_OK


def status_for_bool(value: bool) -> str:
    return STATUS_OK if value else STATUS_WARN


def split_paragraphs(body: str) -> list[str]:
    paragraphs = []
    current: list[str] = []

    for line in body.splitlines():
        if not line.strip():
            if current:
                paragraphs.append("\n".join(current).strip())
                current = []
            continue
        if line.lstrip().startswith(("#", "-", "*", ">", "|")):
            if current:
                paragraphs.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)

    if current:
        paragraphs.append("\n".join(current).strip())

    return [p for p in paragraphs if p]


def heading_report(body: str) -> dict[str, Any]:
    headings = []
    issues = []

    for match in MARKDOWN_HEADING_RE.finditer(body):
        level = len(match.group(1))
        title = match.group(2).strip()
        headings.append({"level": level, "title": title})

    if not headings:
        issues.append("no_markdown_headings")
        return {
            "status": STATUS_WARN,
            "heading_count": 0,
            "top_level_heading_count": 0,
            "issues": issues,
        }

    first_level = headings[0]["level"]
    if first_level > 2:
        issues.append("first_heading_is_deep")

    previous_level = headings[0]["level"]
    for heading in headings[1:]:
        if heading["level"] > previous_level + 1:
            issues.append("heading_level_jump")
            break
        previous_level = heading["level"]

    top_level = min(h["level"] for h in headings)
    top_count = sum(1 for h in headings if h["level"] == top_level)

    status = STATUS_OK
    if issues:
        status = STATUS_WARN
    if len(headings) < 2:
        status = STATUS_WARN

    return {
        "status": status,
        "heading_count": len(headings),
        "top_level_heading_count": top_count,
        "issues": sorted(set(issues)),
    }


def paragraph_report(body: str) -> dict[str, Any]:
    paragraphs = split_paragraphs(body)
    lengths = [len(p) for p in paragraphs]

    if not lengths:
        return {
            "status": STATUS_WARN,
            "paragraph_count": 0,
            "average_paragraph_length": 0,
            "very_long_paragraphs": 0,
            "very_short_paragraphs": 0,
        }

    average = round(sum(lengths) / len(lengths))
    very_long = sum(1 for length in lengths if length > 2500)
    very_short = sum(1 for length in lengths if length < 20)

    status = STATUS_OK
    if average > 1500 or very_long:
        status = STATUS_WARN
    if average > 3000 or very_long > 5:
        status = STATUS_FAIL

    return {
        "status": status,
        "paragraph_count": len(paragraphs),
        "average_paragraph_length": average,
        "very_long_paragraphs": very_long,
        "very_short_paragraphs": very_short,
    }


def assess_cleanliness(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = read_frontmatter_and_body(path)
    has_frontmatter = bool(frontmatter)

    checks = {
        "images_remaining": len(IMAGE_RE.findall(body)),
        "html_tags_remaining": len(HTML_TAG_RE.findall(body)),
        "svg_or_raw_image_tags_remaining": len(SVG_RE.findall(body)),
        "pandoc_spans_remaining": len(PANDOC_SPAN_RE.findall(body)),
        "pandoc_attributes_remaining": len(PANDOC_ATTRIBUTE_RE.findall(body)),
        "pandoc_div_fences_remaining": len(PANDOC_DIV_FENCE_RE.findall(body)),
        "empty_anchors_remaining": len(EMPTY_ANCHOR_RE.findall(body)),
        "raw_html_fences_remaining": len(RAW_HTML_FENCE_RE.findall(body)),
        "epub_artifact_markers": len(EPUB_ID_RE.findall(body)),
        "footnote_backlink_artifacts": len(FOOTNOTE_BACKLINK_RE.findall(body)),
        "non_breaking_spaces": len(NBSP_RE.findall(body)),
        "hard_wrap_splits": len(HARD_WRAP_SPLIT_RE.findall(body)),
    }

    isbn_values = find_isbns_in_text(raw)
    paragraph = paragraph_report(body)
    headings = heading_report(body)

    issue_statuses = {
        "images_remaining": status_for_count(checks["images_remaining"], warn_at=1, fail_at=20),
        "html_tags_remaining": status_for_count(checks["html_tags_remaining"], warn_at=1, fail_at=20),
        "svg_or_raw_image_tags_remaining": status_for_count(checks["svg_or_raw_image_tags_remaining"], warn_at=1, fail_at=3),
        "pandoc_spans_remaining": status_for_count(checks["pandoc_spans_remaining"], warn_at=1, fail_at=50),
        "pandoc_attributes_remaining": status_for_count(checks["pandoc_attributes_remaining"], warn_at=1, fail_at=50),
        "pandoc_div_fences_remaining": status_for_count(checks["pandoc_div_fences_remaining"], warn_at=1, fail_at=10),
        "empty_anchors_remaining": status_for_count(checks["empty_anchors_remaining"], warn_at=1, fail_at=10),
        "raw_html_fences_remaining": status_for_count(checks["raw_html_fences_remaining"], warn_at=1, fail_at=5),
        "epub_artifact_markers": status_for_count(checks["epub_artifact_markers"], warn_at=1, fail_at=20),
        "footnote_backlink_artifacts": status_for_count(checks["footnote_backlink_artifacts"], warn_at=1, fail_at=10),
        "non_breaking_spaces": status_for_count(checks["non_breaking_spaces"], warn_at=1, fail_at=100),
        "hard_wrap_splits": status_for_count(checks["hard_wrap_splits"], warn_at=20, fail_at=500),
        "frontmatter": status_for_bool(has_frontmatter),
        "paragraphs": paragraph["status"],
        "headings": headings["status"],
    }

    status_order = {STATUS_OK: 0, STATUS_WARN: 1, STATUS_FAIL: 2}
    worst = max(issue_statuses.values(), key=lambda item: status_order[item])

    recommendations = []
    if checks["images_remaining"]:
        recommendations.append("Run the cleaner with image removal enabled or review image references manually.")
    if checks["html_tags_remaining"] or checks["svg_or_raw_image_tags_remaining"]:
        recommendations.append("Run the cleaner again or manually remove remaining raw HTML/SVG.")
    if checks["pandoc_spans_remaining"] or checks["pandoc_attributes_remaining"] or checks["empty_anchors_remaining"]:
        recommendations.append("Run the Pandoc/EPUB cleanup profile before indexing.")
    if not has_frontmatter:
        recommendations.append("Generate frontmatter before indexing with `bookmem frontmatter generate --write`.")
    if paragraph["status"] != STATUS_OK:
        recommendations.append("Review paragraph wrapping; long paragraphs can produce poor chunks.")
    if headings["status"] != STATUS_OK:
        recommendations.append("Review Markdown heading structure so chapters and sections are chunked correctly.")
    if not isbn_values:
        recommendations.append("No ISBN found. This may be fine, but catalogue enrichment will be weaker.")

    return {
        "schema_version": 1,
        "clean_check_version": CLEAN_CHECK_VERSION,
        "path": str(path),
        "status": worst,
        "frontmatter": {
            "present": has_frontmatter,
            "status": issue_statuses["frontmatter"],
            "title": frontmatter.get("title") if has_frontmatter else None,
            "author": frontmatter.get("author") if has_frontmatter else None,
        },
        "isbn": {
            "count": len(isbn_values),
            "values": isbn_values,
        },
        "checks": checks,
        "statuses": issue_statuses,
        "paragraphs": paragraph,
        "headings": headings,
        "recommendations": recommendations,
    }


def clean_check_many(paths: list[Path]) -> list[dict[str, Any]]:
    return [assess_cleanliness(path) for path in paths]


def summarise_clean_check(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": report["path"],
        "status": report["status"],
        "images_remaining": report["checks"]["images_remaining"],
        "html_tags_remaining": report["checks"]["html_tags_remaining"],
        "pandoc_spans_remaining": report["checks"]["pandoc_spans_remaining"],
        "empty_anchors_remaining": report["checks"]["empty_anchors_remaining"],
        "average_paragraph_length": report["paragraphs"]["average_paragraph_length"],
        "heading_structure": report["headings"]["status"],
        "isbn_count": report["isbn"]["count"],
        "frontmatter": "present" if report["frontmatter"]["present"] else "missing",
    }
