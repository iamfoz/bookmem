from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any

import yaml

from .chunking import FRONTMATTER_RE, slugify
from .config import get_settings
from .taxonomy import get_class_label, infer_class_from_path, normalise_alias
from .book_files import discover_book_markdown_files


# Filename convention supported by BookMem:
#   <Title> - <Author> - <ISBN>.md
# ISBN is optional. The parser works from the right-hand side so titles and author
# names may themselves contain hyphens.
ISBN_TOKEN_RE = re.compile(r"^(?:ISBN(?:-1[03])?:?\s*)?(?P<isbn>(?:97[89][\-\s]?)?(?:\d[\-\s]?){9,12}[\dXx])$")
ISBN_RE = re.compile(r"\b(?:97[89][\-\s]?)?(?:\d[\-\s]?){9,12}[\dXx]\b")
ISBN_LABELLED_RE = re.compile(r"(?i)ISBN(?:-1[03])?:?\s*((?:97[89][\-\s]?)?(?:\d[\-\s]?){9,12}[\dXx])")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class ParsedFilename:
    title: str
    author: str | None = None
    isbn: str | None = None
    confidence: str = "low"


@dataclass
class FrontmatterResult:
    path: str
    had_existing_frontmatter: bool
    wrote_file: bool
    title: str
    author: str | None
    isbn: str | None
    primary_class: str
    primary_label: str
    classification_source: str
    routing_aliases: list[str]
    topics: list[str]


def read_markdown_with_frontmatter(path: Path) -> tuple[dict[str, Any], str, bool]:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text, False

    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        data = {}
    return data, text[match.end():], True


def write_markdown_with_frontmatter(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    yaml_text = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    ).strip()
    path.write_text(f"---\n{yaml_text}\n---\n\n{body.lstrip()}", encoding="utf-8")


def is_valid_isbn10(value: str) -> bool:
    if not re.fullmatch(r"\d{9}[\dXx]", value):
        return False
    total = 0
    for idx, char in enumerate(value.upper(), start=1):
        digit = 10 if char == "X" else int(char)
        total += idx * digit
    return total % 11 == 0


def is_valid_isbn13(value: str) -> bool:
    if not re.fullmatch(r"\d{13}", value):
        return False
    total = 0
    for idx, char in enumerate(value[:12]):
        total += int(char) * (1 if idx % 2 == 0 else 3)
    check = (10 - (total % 10)) % 10
    return check == int(value[-1])


def normalise_isbn(value: str | None, validate: bool = True) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"(?i)^ISBN(?:-1[03])?:?\s*", "", value.strip())
    cleaned = re.sub(r"[\s-]", "", cleaned).upper()
    if len(cleaned) == 10 and re.fullmatch(r"\d{9}[\dX]", cleaned):
        return cleaned if not validate or is_valid_isbn10(cleaned) else None
    if len(cleaned) == 13 and re.fullmatch(r"\d{13}", cleaned):
        return cleaned if not validate or is_valid_isbn13(cleaned) else None
    return None


def find_isbns_in_text(text: str, max_chars: int | None = None) -> list[str]:
    """Find likely ISBNs in Markdown text, deduplicated and checksum-validated.

    Labelled ISBNs are preferred, but the function also scans for bare ISBN-like
    strings because exported EPUB/PDF Markdown often has catalogue data without
    consistent labels.
    """
    haystack = text[:max_chars] if max_chars else text
    candidates: list[str] = []

    for match in ISBN_LABELLED_RE.finditer(haystack):
        normalised = normalise_isbn(match.group(1))
        if normalised:
            candidates.append(normalised)

    for match in ISBN_RE.finditer(haystack):
        normalised = normalise_isbn(match.group(0))
        if not normalised:
            continue
        # Bare ISBN-13s are distinctive because they start 978/979. Bare ISBN-10s
        # are much easier to confuse with page IDs, image dimensions or catalogue
        # fragments, so only accept them when the nearby text actually mentions ISBN.
        if len(normalised) == 13:
            candidates.append(normalised)
        else:
            context = haystack[max(0, match.start() - 20): match.end() + 20]
            if re.search(r"(?i)ISBN", context):
                candidates.append(normalised)

    seen: set[str] = set()
    results: list[str] = []
    # Prefer ISBN-13 over ISBN-10 when both are present, because LoC lookup tends
    # to be more reliable with modern ISBN-13 values.
    for isbn in sorted(candidates, key=lambda item: (len(item) != 13, item)):
        if isbn not in seen:
            seen.add(isbn)
            results.append(isbn)
    return results


def parse_book_filename(path: Path) -> ParsedFilename:
    """Parse '<Title> - <Author> - <ISBN>.md' without being confused by hyphens in title.

    We intentionally split on ' - ' rather than any hyphen, because book titles often contain
    punctuation such as em dashes, colons, subtitles and hyphenated phrases.
    """
    stem = path.stem.strip()
    parts = [part.strip() for part in stem.split(" - ") if part.strip()]

    if not parts:
        return ParsedFilename(title=path.stem, confidence="low")

    isbn: str | None = None
    if len(parts) >= 2:
        isbn_match = ISBN_TOKEN_RE.match(parts[-1])
        if isbn_match:
            isbn = normalise_isbn(isbn_match.group("isbn"))
            parts = parts[:-1]

    author: str | None = None
    if len(parts) >= 2:
        author = parts[-1]
        title = " - ".join(parts[:-1])
        confidence = "high" if isbn else "medium"
    else:
        title = parts[0]
        confidence = "medium" if isbn else "low"

    return ParsedFilename(title=title.strip(), author=author, isbn=isbn, confidence=confidence)


def infer_title_author_isbn(path: Path, existing: dict[str, Any], body: str) -> tuple[str, str | None, dict[str, str], ParsedFilename]:
    parsed = parse_book_filename(path)

    title = existing.get("title") or parsed.title
    author = existing.get("author") or parsed.author
    isbn_data: dict[str, str] = {}

    existing_isbn = existing.get("isbn")
    if isinstance(existing_isbn, dict):
        for key, value in existing_isbn.items():
            normalised = normalise_isbn(str(value))
            if normalised:
                isbn_data[str(key)] = normalised
    elif isinstance(existing_isbn, str):
        normalised = normalise_isbn(existing_isbn)
        if normalised:
            isbn_data["unknown"] = normalised

    detected_isbns = find_isbns_in_text(body)

    if parsed.isbn and "filename" not in isbn_data:
        isbn_data["filename"] = parsed.isbn

    if detected_isbns:
        if "detected_in_text" not in isbn_data:
            isbn_data["detected_in_text"] = detected_isbns[0]
        for idx, detected in enumerate(detected_isbns[:10], start=1):
            key = f"detected_in_text_{idx}"
            if detected not in isbn_data.values():
                isbn_data[key] = detected

    return str(title).strip(), str(author).strip() if author else None, isbn_data, parsed


def infer_topics_from_text(body: str, limit: int = 12) -> list[str]:
    headings = [h.strip() for h in HEADING_RE.findall(body)]
    candidates: list[str] = []

    # Headings are often the best cheap signal for book-level retrieval topics.
    for heading in headings[:80]:
        cleaned = re.sub(r"^(chapter|part|section)\s+\d+[:.\s-]*", "", heading, flags=re.I).strip()
        cleaned = cleaned.strip(" .:-")
        if not cleaned or cleaned.lower() in {"introduction", "preface", "conclusion", "notes"}:
            continue
        if len(cleaned) <= 80:
            candidates.append(cleaned.lower())

    keyword_map = {
        "systems": "systems",
        "goals": "goals",
        "habit": "habits",
        "energy": "personal energy",
        "failure": "failure",
        "finance": "finance",
        "invest": "investing",
        "money": "money",
        "productivity": "productivity",
        "decision": "decision-making",
        "psychology": "psychology",
        "health": "health",
        "sleep": "sleep",
        "leadership": "leadership",
        "management": "management",
        "writing": "writing",
        "creativity": "creativity",
        "ai": "AI",
        "software": "software",
    }
    lower = body[:60000].lower()
    for key, topic in keyword_map.items():
        if key in lower:
            candidates.append(topic)

    seen: set[str] = set()
    topics: list[str] = []
    for item in candidates:
        normalised = normalise_alias(item).replace("_", " ")
        if normalised not in seen:
            seen.add(normalised)
            topics.append(item)
        if len(topics) >= limit:
            break
    return topics


def class_aliases(primary_class: str) -> list[str]:
    mapping = {
        "004": ["technology", "computing"],
        "005": ["technology", "software"],
        "006": ["technology", "ai"],
        "150": ["psychology"],
        "153": ["psychology", "decision_making"],
        "158": ["personal_development", "productivity"],
        "330": ["finance", "economics"],
        "332": ["finance", "investing"],
        "338": ["business", "entrepreneurship"],
        "610": ["health"],
        "613": ["health", "wellbeing"],
        "650": ["business", "productivity"],
        "658": ["business", "management"],
        "780": ["music", "creativity"],
        "808": ["writing", "creativity"],
    }
    return mapping.get(primary_class, [])


def infer_class_from_metadata(title: str, author: str | None, body: str, topics: list[str]) -> tuple[str | None, str | None, str]:
    """Suggest a BMDC class using filename/frontmatter text and headings.

    This uses weighted scoring rather than first-match rules. Titles, authors and
    headings are deliberately weighted more heavily than the body because many
    narrative/non-fiction books mention money, health, work or technology without
    primarily belonging to those classes.
    """
    title_text = " ".join([title, author or "", " ".join(topics)]).lower()
    body_text = body[:30000].lower()

    rules: dict[str, list[str]] = {
        "332": ["investing", "investor", "investment", "stock", "stocks", "fund", "funds", "portfolio", "finance", "financial", "money", "wealth", "market", "markets", "banking", "compound interest", "retirement"],
        "330": ["economics", "economic", "economy", "capitalism", "inflation", "macroeconomics", "microeconomics"],
        "158": ["habit", "habits", "self improvement", "self-improvement", "personal development", "success", "motivation", "mindset", "goals", "systems", "productivity", "confidence", "discipline", "willpower", "energy", "failure"],
        "153": ["decision", "decisions", "thinking", "focus", "attention", "memory", "cognitive", "bias", "biases", "intelligence"],
        "650": ["work", "career", "productivity", "office", "time management", "business skills"],
        "658": ["leadership", "management", "manager", "operations", "strategy", "execution", "organisation", "organization"],
        "338": ["startup", "startups", "entrepreneur", "entrepreneurship", "enterprise", "industry"],
        "613": ["sleep", "nutrition", "exercise", "fitness", "wellbeing", "well-being", "supplements", "diet", "health"],
        "610": ["medicine", "medical", "doctor", "clinical", "diagnosis", "therapy"],
        "006": ["artificial intelligence", "machine learning", "llm", "agents", "ai ", " ai"],
        "005": ["programming", "software", "python", "code", "coding", "database"],
        "808": ["writing", "storytelling", "copywriting", "rhetoric"],
        "780": ["music", "songwriting", "songs", "recording", "mixing", "mastering"],
        "920": ["biography", "memoir", "autobiography", "life of"],
    }

    scores: dict[str, int] = {}
    for class_code, keywords in rules.items():
        score = 0
        for keyword in keywords:
            if keyword in title_text:
                score += 8
            if keyword in body_text:
                score += 1
        if score:
            scores[class_code] = score

    if not scores:
        return None, None, "unclassified"

    # Specific tie-breaks for common BookMem categories.
    # A book whose title/headings strongly signal self-improvement should not be
    # dragged into finance merely because it contains anecdotes about money.
    if scores.get("158", 0) >= 8 and scores.get("158", 0) >= scores.get("332", 0) - 2:
        best = "158"
    else:
        best = max(scores.items(), key=lambda item: item[1])[0]

    return best, get_class_label(best), "filename/content keyword"


def build_frontmatter(path: Path, body: str, existing: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    title, author, isbn, parsed = infer_title_author_isbn(path, existing, body)

    existing_classification = existing.get("classification") or {}
    if not isinstance(existing_classification, dict):
        existing_classification = {}

    inferred_from_path, inferred_label_from_path = infer_class_from_path(path, settings.books_dir)
    topics = existing_classification.get("topics") or infer_topics_from_text(body)
    if isinstance(topics, str):
        topics = [topics]

    metadata_class, metadata_label, metadata_source = infer_class_from_metadata(title, author, body, [str(item) for item in topics])

    if existing_classification.get("primary_class") or existing.get("primary_class"):
        primary_class = str(existing_classification.get("primary_class") or existing.get("primary_class"))
        classification_source = "existing_frontmatter"
    elif inferred_from_path != "999":
        primary_class = inferred_from_path
        classification_source = "folder_path"
    elif metadata_class:
        primary_class = metadata_class
        classification_source = metadata_source
    else:
        primary_class = "999"
        classification_source = "unclassified"

    primary_label = str(
        existing_classification.get("primary_label")
        or existing.get("primary_class_label")
        or get_class_label(primary_class)
        or inferred_label_from_path
        or metadata_label
        or "Unclassified"
    )

    secondary_classes = existing_classification.get("secondary_classes") or existing_classification.get("secondary_class") or []
    if isinstance(secondary_classes, str):
        secondary_classes = [secondary_classes]

    routing_aliases = existing_classification.get("routing_aliases") or class_aliases(primary_class)
    if isinstance(routing_aliases, str):
        routing_aliases = [routing_aliases]

    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    frontmatter: dict[str, Any] = {
        "bookmem": {
            "schema_version": 1,
            "source_type": "markdown_book",
            "source_status": existing.get("bookmem", {}).get("source_status", "cleaned")
            if isinstance(existing.get("bookmem"), dict)
            else "cleaned",
        },
        "title": title,
        "author": author,
    }

    if isbn:
        frontmatter["isbn"] = isbn

    frontmatter["classification"] = {
        "scheme": "BMDC",
        "primary_class": primary_class,
        "primary_label": primary_label,
        "secondary_classes": [str(item) for item in secondary_classes],
        "routing_aliases": [normalise_alias(str(item)) for item in routing_aliases],
        "topics": [str(item) for item in topics],
    }

    frontmatter["metadata"] = {
        "filename_title": parsed.title,
        "filename_author": parsed.author,
        "filename_isbn": parsed.isbn,
        "filename_parse_confidence": parsed.confidence,
        "detected_text_isbns": find_isbns_in_text(body),
        "classification_source": classification_source,
    }

    source = existing.get("source") if isinstance(existing.get("source"), dict) else {}
    frontmatter["source"] = {
        "original_path": source.get("original_path", ""),
        "cleaned_path": str(path),
    }

    ingest = existing.get("ingest") if isinstance(existing.get("ingest"), dict) else {}
    frontmatter["ingest"] = {
        "include": ingest.get("include", True),
        "chunk_profile": ingest.get("chunk_profile", "standard_nonfiction"),
        "frontmatter_generated_at": now,
    }

    # Preserve any extra top-level keys not owned by the generator.
    managed_keys = {"bookmem", "title", "author", "isbn", "classification", "metadata", "source", "ingest"}
    for key, value in existing.items():
        if key not in managed_keys:
            frontmatter[key] = value

    return frontmatter


def generate_frontmatter(
    path: Path,
    write: bool = False,
    overwrite: bool = False,
) -> tuple[FrontmatterResult, dict[str, Any], str]:
    existing, body, had_existing = read_markdown_with_frontmatter(path)
    if had_existing and not overwrite:
        frontmatter = existing
        wrote = False
    else:
        frontmatter = build_frontmatter(path, body, existing)
        wrote = False
        if write:
            write_markdown_with_frontmatter(path, frontmatter, body)
            wrote = True

    classification = frontmatter.get("classification") or {}
    if not isinstance(classification, dict):
        classification = {}

    isbn = frontmatter.get("isbn") or {}
    isbn_value = None
    if isinstance(isbn, dict) and isbn:
        isbn_value = next(iter(isbn.values()))
    elif isinstance(isbn, str):
        isbn_value = isbn

    metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}

    result = FrontmatterResult(
        path=str(path),
        had_existing_frontmatter=had_existing,
        wrote_file=wrote,
        title=str(frontmatter.get("title", path.stem)),
        author=str(frontmatter.get("author")) if frontmatter.get("author") else None,
        isbn=str(isbn_value) if isbn_value else None,
        primary_class=str(classification.get("primary_class", "999")),
        primary_label=str(classification.get("primary_label", "Unclassified")),
        classification_source=str(metadata.get("classification_source", "unknown")),
        routing_aliases=list(classification.get("routing_aliases") or []),
        topics=list(classification.get("topics") or []),
    )
    return result, frontmatter, body


def validate_frontmatter(path: Path) -> list[str]:
    existing, _body, had_existing = read_markdown_with_frontmatter(path)
    errors: list[str] = []
    if not had_existing:
        errors.append("Missing YAML frontmatter block")
        return errors

    for key in ["title", "author", "classification"]:
        if not existing.get(key):
            errors.append(f"Missing required field: {key}")

    classification = existing.get("classification")
    if not isinstance(classification, dict):
        errors.append("classification must be a mapping")
        return errors

    if not classification.get("primary_class"):
        errors.append("Missing classification.primary_class")
    if not classification.get("primary_label"):
        errors.append("Missing classification.primary_label")
    if classification.get("scheme") != "BMDC":
        errors.append("classification.scheme should be BMDC")

    return errors


def book_id_from_frontmatter(path: Path) -> str:
    existing, body, _ = read_markdown_with_frontmatter(path)
    title, author, _isbn, _parsed = infer_title_author_isbn(path, existing, body)
    return slugify(f"{author or ''}_{title}")



def discover_book_files(root: Path | str) -> list[Path]:
    """Return Markdown book files under root.

    Backwards-compatible helper used by doctor/API/MCP/notes modules.
    """
    return discover_book_markdown_files(root)


def read_frontmatter_and_body(path: Path | str) -> tuple[dict, str]:
    """Read Markdown frontmatter and body.

    Backwards-compatible wrapper around read_markdown_with_frontmatter.
    """
    frontmatter, body, _had_frontmatter = read_markdown_with_frontmatter(Path(path))
    return frontmatter, body
