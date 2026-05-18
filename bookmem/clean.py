from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import re

import yaml


CLEANER_VERSION = "0.2.0"


@dataclass
class CleanReport:
    source_path: str
    output_path: str | None
    original_chars: int
    cleaned_chars: int
    removed_chars: int
    removed_images: int
    removed_anchors: int
    removed_div_fences: int
    removed_raw_html_blocks: int
    removed_span_attributes: int
    normalised_headings: int
    dropped_front_matter: bool
    profile: str = "epub_pandoc"


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^\)]*\)(?:\{[^}]*\})?")
EMPTY_ANCHOR_RE = re.compile(r"\[\]\{#[^}]+\}")
SPAN_ATTR_RE = re.compile(r"\[([^\[\]]*?)\]\{[^}]*\}")
RAW_ATTR_RE = re.compile(r"\{=[a-zA-Z0-9_-]+\}")
HTML_TAG_RE = re.compile(r"</?[^>]+>")
DIV_FENCE_LINE_RE = re.compile(r"^\s*:{3,}.*$", re.MULTILINE)
HR_RE = re.compile(r"^\s*(?:-{5,}|_{5,}|\*{5,})\s*$", re.MULTILINE)
IDGEN_LINE_RE = re.compile(r"^\s*(?:_idGen|\. _idGen|#HtFa|HtFa|\{#HtFa).*?$", re.MULTILINE)
SVG_BLOCK_RE = re.compile(r":::.*?\n\s*<svg\b.*?</svg>\s*\n:::\s*", re.DOTALL | re.IGNORECASE)
HTML_BLOCK_RE = re.compile(r"<svg\b.*?</svg>", re.DOTALL | re.IGNORECASE)
FOOTNOTE_LINK_RE = re.compile(r"\[+([*†‡§¶#0-9,\- ]+)\]+\([^\)]*footnote[^\)]*\)(?:\{[^}]*\})?")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^\)]*)\)")
BLOCKQUOTE_RE = re.compile(r"^\s*>.*$", re.MULTILINE)
MULTI_BLANK_RE = re.compile(r"\n{3,}")

CHAPTER_NUM_RE = re.compile(r"^Chapter\s+(\d+|[IVXLCDM]+)\s*$", re.IGNORECASE)
CONTENT_START_RE = re.compile(
    r"^(?:Preface(?:\s+to\s+the\s+.+)?|Introduction|Prologue|Chapter\s+\d+|Chapter\s+[IVXLCDM]+)\s*$",
    re.IGNORECASE,
)


DEFAULT_PROFILE_NAME = "epub_pandoc"


DEFAULT_PROFILE: dict[str, Any] = {
    "drop_pre_content_matter": True,
    "remove_images": True,
    "remove_html": True,
    "remove_raw_html_blocks": True,
    "remove_empty_anchors": True,
    "remove_div_fences": True,
    "strip_spans": True,
    "strip_pandoc_attributes": True,
    "remove_footnote_links": True,
    "strip_link_targets": True,
    "remove_horizontal_rules": True,
    "remove_idgen_lines": True,
    "normalise_inline_noise": True,
    "join_wrapped_lines": True,
    "normalise_headings": True,
    "remove_blockquotes": False,
    "preserve_lists": True,
}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_cleaning_profiles() -> dict[str, dict[str, Any]]:
    """Load built-in and user-defined cleaning profiles from config YAML."""
    profiles: dict[str, dict[str, Any]] = {}

    base_path = Path("config/cleaning_profiles.yaml")
    if base_path.exists():
        loaded = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
        profiles.update(loaded.get("cleaning_profiles", {}))

    profiles_dir = Path("config/cleaning_profiles.d")
    if profiles_dir.exists():
        for path in sorted(profiles_dir.glob("*.y*ml")):
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            profiles.update(loaded.get("cleaning_profiles", {}))

    if DEFAULT_PROFILE_NAME not in profiles:
        profiles[DEFAULT_PROFILE_NAME] = dict(DEFAULT_PROFILE)

    return profiles


def resolve_cleaning_profile(profile: str | dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    profiles = load_cleaning_profiles()

    if profile is None:
        name = DEFAULT_PROFILE_NAME
        raw = profiles.get(name, {})
    elif isinstance(profile, dict):
        name = str(profile.get("name") or "custom")
        raw = profile
    else:
        name = profile
        if name not in profiles:
            raise KeyError(f"Unknown cleaning profile: {name}")
        raw = profiles[name]

    # Support inheritance.
    parent_name = raw.get("extends")
    if parent_name:
        if parent_name not in profiles:
            raise KeyError(f"Cleaning profile {name} extends unknown profile {parent_name}")
        parent = resolve_cleaning_profile(parent_name)[1]
        merged = _deep_merge(parent, raw)
    else:
        merged = _deep_merge(DEFAULT_PROFILE, raw)

    merged["name"] = name
    return name, merged


def validate_cleaning_profiles() -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    profiles = load_cleaning_profiles()

    bool_keys = set(DEFAULT_PROFILE.keys())

    for name, profile in sorted(profiles.items()):
        if not isinstance(profile, dict):
            issues.append({"profile": name, "issue": "invalid_profile", "message": "Profile must be a mapping."})
            continue
        try:
            _resolved_name, resolved = resolve_cleaning_profile(name)
        except Exception as exc:
            issues.append({"profile": name, "issue": "resolve_failed", "message": str(exc)})
            continue

        for key in bool_keys:
            if key in resolved and not isinstance(resolved[key], bool):
                issues.append({"profile": name, "issue": "invalid_value", "message": f"{key} must be true or false."})

    return issues


def _strip_yaml_frontmatter(text: str) -> tuple[str | None, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    return match.group(0), text[match.end():]


def _restore_yaml_frontmatter(frontmatter: str | None, body: str) -> str:
    if not frontmatter:
        return body
    return frontmatter.rstrip() + "\n\n" + body.lstrip()


def _drop_pre_content_matter(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        candidate = line.strip()
        if idx + 1 < len(lines):
            candidate_two_lines = f"{candidate} {lines[idx + 1].strip()}".strip()
        else:
            candidate_two_lines = candidate
        if CONTENT_START_RE.match(candidate) or CONTENT_START_RE.match(candidate_two_lines):
            return "\n".join(lines[idx:]), idx > 0
    return text, False


def _normalise_pandoc_spans(text: str) -> tuple[str, int]:
    count = 0
    previous = None
    while previous != text:
        previous = text
        text, n = SPAN_ATTR_RE.subn(lambda m: m.group(1), text)
        count += n
    return text, count


def _remove_raw_blocks(text: str) -> tuple[str, int]:
    text, n1 = SVG_BLOCK_RE.subn("\n", text)
    text, n2 = HTML_BLOCK_RE.subn("\n", text)
    return text, n1 + n2


def _remove_visual_noise(text: str, profile: dict[str, Any]) -> tuple[str, dict[str, int]]:
    stats = {
        "removed_raw_html_blocks": 0,
        "removed_images": 0,
        "removed_anchors": 0,
        "removed_div_fences": 0,
        "removed_span_attributes": 0,
    }

    if profile.get("remove_raw_html_blocks", True):
        text, stats["removed_raw_html_blocks"] = _remove_raw_blocks(text)

    if profile.get("remove_images", True):
        text, stats["removed_images"] = IMAGE_RE.subn("", text)

    if profile.get("remove_empty_anchors", True):
        text, stats["removed_anchors"] = EMPTY_ANCHOR_RE.subn("", text)

    if profile.get("remove_div_fences", True):
        text, stats["removed_div_fences"] = DIV_FENCE_LINE_RE.subn("", text)

    if profile.get("strip_spans", True):
        text, n = _normalise_pandoc_spans(text)
        stats["removed_span_attributes"] += n

    if profile.get("remove_footnote_links", True):
        text = FOOTNOTE_LINK_RE.sub(lambda m: m.group(1).strip(), text)

    if profile.get("strip_link_targets", True):
        text = MARKDOWN_LINK_RE.sub(lambda m: m.group(1), text)

    if profile.get("strip_pandoc_attributes", True):
        text = RAW_ATTR_RE.sub("", text)
        text = re.sub(r"\{\.[^}]+\}", "", text)
        text = re.sub(r"\{#[^}]+\}", "", text)

    if profile.get("remove_html", True):
        text = HTML_TAG_RE.sub("", text)

    if profile.get("remove_horizontal_rules", True):
        text = HR_RE.sub("", text)

    if profile.get("remove_idgen_lines", True):
        text = IDGEN_LINE_RE.sub("", text)

    if profile.get("remove_blockquotes", False):
        text = BLOCKQUOTE_RE.sub("", text)

    return text, stats


def _strip_inline_markdown_noise(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\\|", "|")
    text = text.replace("\\$", "$")
    text = text.replace("\\@", "@")
    text = text.replace("\\--", "--")
    text = text.replace("---", "—")
    return text


def _join_wrapped_lines(text: str, profile: dict[str, Any]) -> str:
    out: list[str] = []
    para: list[str] = []

    def flush() -> None:
        nonlocal para
        if para:
            out.append(_join_paragraph_lines(para))
            para = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue

        if _is_structural_line(line, profile):
            flush()
            out.append(line)
            continue

        para.append(line)

    flush()
    return "\n\n".join(out)


def _is_structural_line(line: str, profile: dict[str, Any] | None = None) -> bool:
    profile = profile or DEFAULT_PROFILE
    if line.startswith("#"):
        return True
    if profile.get("preserve_lists", True):
        if re.match(r"^[-*+]\s+", line):
            return True
        if re.match(r"^\d+[.)]\s+", line):
            return True
    if not profile.get("remove_blockquotes", False) and line.startswith(">"):
        return True
    if CHAPTER_NUM_RE.match(line):
        return True
    if CONTENT_START_RE.match(line):
        return True
    return False


def _join_paragraph_lines(lines: list[str]) -> str:
    text = ""
    for line in lines:
        if not text:
            text = line
            continue
        text += " " + line
    return re.sub(r"\s+", " ", text).strip()


def _normalise_headings(text: str, profile: dict[str, Any]) -> tuple[str, int]:
    lines = text.splitlines()
    out: list[str] = []
    changed = 0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

        chapter_match = CHAPTER_NUM_RE.match(line)
        if chapter_match:
            if next_line and not _is_structural_line(next_line, profile):
                out.append(f"## Chapter {chapter_match.group(1)}: {next_line}")
                changed += 1
                i += 2
                continue
            out.append(f"## Chapter {chapter_match.group(1)}")
            changed += 1
            i += 1
            continue

        combined = f"{line} {next_line}".strip() if next_line else line
        if CONTENT_START_RE.match(combined) and not line.startswith("#"):
            out.append(f"# {combined}")
            changed += 1
            i += 2 if next_line and combined != line else 1
            continue

        if CONTENT_START_RE.match(line) and not line.startswith("#"):
            out.append(f"# {line}")
            changed += 1
            i += 1
            continue

        out.append(lines[i].rstrip())
        i += 1

    return "\n".join(out), changed


def _final_tidy(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip() + "\n"


def clean_markdown_text(
    text: str,
    drop_front_matter: bool = True,
    profile: str | dict[str, Any] | None = None,
) -> tuple[str, dict[str, int | bool | str]]:
    original_len = len(text)
    profile_name, resolved_profile = resolve_cleaning_profile(profile)

    # CLI compatibility: explicit drop_front_matter=False always wins.
    if not drop_front_matter:
        resolved_profile["drop_pre_content_matter"] = False

    frontmatter, body = _strip_yaml_frontmatter(text)

    body, stats = _remove_visual_noise(body, resolved_profile)

    if resolved_profile.get("normalise_inline_noise", True):
        body = _strip_inline_markdown_noise(body)

    dropped = False
    if resolved_profile.get("drop_pre_content_matter", True):
        body, dropped = _drop_pre_content_matter(body)

    if resolved_profile.get("join_wrapped_lines", True):
        body = _join_wrapped_lines(body, resolved_profile)

    heading_count = 0
    if resolved_profile.get("normalise_headings", True):
        body, heading_count = _normalise_headings(body, resolved_profile)

    body = _final_tidy(body)
    cleaned = _restore_yaml_frontmatter(frontmatter, body)

    stats["normalised_headings"] = heading_count
    stats["dropped_front_matter"] = dropped
    stats["original_chars"] = original_len
    stats["cleaned_chars"] = len(cleaned)
    stats["removed_chars"] = max(0, original_len - len(cleaned))
    stats["profile"] = profile_name
    return cleaned, stats


def clean_markdown_file(
    source_path: Path,
    output_path: Path | None = None,
    in_place: bool = False,
    drop_front_matter: bool = True,
    profile: str | dict[str, Any] | None = None,
) -> CleanReport:
    if in_place and output_path is not None:
        raise ValueError("Use either output_path or in_place, not both")

    original = source_path.read_text(encoding="utf-8", errors="replace")
    cleaned, stats = clean_markdown_text(
        original,
        drop_front_matter=drop_front_matter,
        profile=profile,
    )

    destination: Path | None = None
    if in_place:
        destination = source_path
    elif output_path is not None:
        destination = output_path

    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(cleaned, encoding="utf-8")

    return CleanReport(
        source_path=str(source_path),
        output_path=str(destination) if destination else None,
        original_chars=int(stats["original_chars"]),
        cleaned_chars=int(stats["cleaned_chars"]),
        removed_chars=int(stats["removed_chars"]),
        removed_images=int(stats["removed_images"]),
        removed_anchors=int(stats["removed_anchors"]),
        removed_div_fences=int(stats["removed_div_fences"]),
        removed_raw_html_blocks=int(stats["removed_raw_html_blocks"]),
        removed_span_attributes=int(stats["removed_span_attributes"]),
        normalised_headings=int(stats["normalised_headings"]),
        dropped_front_matter=bool(stats["dropped_front_matter"]),
        profile=str(stats.get("profile") or DEFAULT_PROFILE_NAME),
    )


def report_as_dict(report: CleanReport) -> dict[str, object]:
    return asdict(report)
