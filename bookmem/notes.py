"""Obsidian-friendly note generation for BookMem."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import textwrap
from typing import Any

import yaml

from .config import get_settings
from .frontmatter import discover_book_files, read_frontmatter_and_body
from .summaries import summary_paths, load_book_summary
from .search import search_books
from .taxonomy import load_taxonomy


NOTE_GENERATOR_VERSION = "0.1.0"


def slugify_filename(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or "Untitled"


def yaml_dump(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()


def load_note_templates() -> dict[str, Any]:
    settings = get_settings()
    base_path = Path("config/note_templates.yaml")
    templates: dict[str, Any] = {}

    if base_path.exists():
        loaded = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
        templates.update(loaded.get("templates", {}))

    templates_dir = Path("config/note_templates.d")
    if templates_dir.exists():
        for path in sorted(templates_dir.glob("*.y*ml")):
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            templates.update(loaded.get("templates", {}))

    return templates


def normalise_tags(values: list[Any]) -> list[str]:
    tags = []
    for value in values or []:
        text = str(value).strip()
        if not text:
            continue
        text = text.replace(" ", "-").replace("/", "-").lower()
        text = re.sub(r"[^a-z0-9_-]+", "", text)
        if text:
            tags.append(text)
    return sorted(dict.fromkeys(tags))


def display_title_from_frontmatter(frontmatter: dict[str, Any]) -> str:
    return str(frontmatter.get("title") or "Untitled").strip()


def display_author_from_frontmatter(frontmatter: dict[str, Any]) -> str:
    return str(frontmatter.get("author") or "Unknown author").strip()


def safe_book_id(frontmatter: dict[str, Any], path: Path) -> str:
    existing = frontmatter.get("book_id")
    if existing:
        return str(existing)
    base = f"{frontmatter.get('author', '')}_{frontmatter.get('title', path.stem)}".lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    return re.sub(r"_+", "_", base).strip("_") or path.stem


def extract_classification(frontmatter: dict[str, Any]) -> dict[str, Any]:
    classification = frontmatter.get("classification", {}) or {}
    return {
        "class": classification.get("primary_class"),
        "class_label": classification.get("primary_label"),
        "secondary_classes": classification.get("secondary_classes", []),
        "routing_aliases": classification.get("routing_aliases", []),
        "topics": classification.get("topics", []),
    }


def note_frontmatter(
    book_path: Path,
    book_frontmatter: dict[str, Any],
    note_type: str,
) -> dict[str, Any]:
    classification = extract_classification(book_frontmatter)
    title = display_title_from_frontmatter(book_frontmatter)
    author = display_author_from_frontmatter(book_frontmatter)
    topics = classification.get("topics") or []
    aliases = classification.get("routing_aliases") or []

    tags = normalise_tags(["book", note_type, *topics, *aliases])

    return {
        "type": "book-note",
        "note_type": note_type,
        "book_id": safe_book_id(book_frontmatter, book_path),
        "title": title,
        "author": author,
        "isbn": book_frontmatter.get("isbn"),
        "class": classification.get("class"),
        "class_label": classification.get("class_label"),
        "topics": topics,
        "routing_aliases": aliases,
        "source_book": str(book_path),
        "generator": "bookmem",
        "generator_version": NOTE_GENERATOR_VERSION,
        "review_status": "machine_draft",
        "tags": tags,
    }


def bullet_list(values: list[Any], fallback: str = "Not yet available.") -> str:
    cleaned = [str(v).strip() for v in values or [] if str(v).strip()]
    if not cleaned:
        return fallback
    return "\n".join(f"- {value}" for value in cleaned)


def paragraph(value: Any, fallback: str = "Not yet available.") -> str:
    if value is None:
        return fallback
    if isinstance(value, list):
        return bullet_list(value, fallback=fallback)
    text = str(value).strip()
    return text if text else fallback


def load_existing_summary_for_book(book_path: Path, frontmatter: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    book_id = safe_book_id(frontmatter, book_path)
    book_summary_path, chapters_path = summary_paths(book_id)
    data: dict[str, Any] = {}

    if book_summary_path.exists():
        data["book_summary"] = yaml.safe_load(book_summary_path.read_text(encoding="utf-8")) or {}
    if chapters_path.exists():
        data["chapters"] = yaml.safe_load(chapters_path.read_text(encoding="utf-8")) or {}

    return data


def fallback_core_thesis(frontmatter: dict[str, Any], summary_data: dict[str, Any]) -> str:
    summary = summary_data.get("book_summary", {})
    for key in ("core_thesis", "summary", "description"):
        value = summary.get(key)
        if value:
            return str(value).strip()

    topics = extract_classification(frontmatter).get("topics") or []
    title = display_title_from_frontmatter(frontmatter)
    if topics:
        return (
            f"*{title}* appears most relevant to: "
            + ", ".join(str(t) for t in topics[:8])
            + ". Review and replace this machine-draft thesis."
        )
    return "Machine-draft placeholder. Review the book and add a concise core thesis."


def fallback_major_ideas(frontmatter: dict[str, Any], summary_data: dict[str, Any]) -> list[str]:
    summary = summary_data.get("book_summary", {})
    for key in ("major_ideas", "key_ideas", "themes"):
        value = summary.get(key)
        if isinstance(value, list) and value:
            return [str(v) for v in value]
    topics = extract_classification(frontmatter).get("topics") or []
    return [str(t) for t in topics[:10]]


def fallback_questions(frontmatter: dict[str, Any], summary_data: dict[str, Any]) -> list[str]:
    summary = summary_data.get("book_summary", {})
    for key in ("best_for_questions_about", "questions", "useful_for"):
        value = summary.get(key)
        if isinstance(value, list) and value:
            return [str(v) for v in value]

    topics = extract_classification(frontmatter).get("topics") or []
    title = display_title_from_frontmatter(frontmatter)
    return [f"What does {title} say about {topic}?" for topic in topics[:8]]


def useful_passages(book_path: Path, frontmatter: dict[str, Any], limit: int = 5) -> list[str]:
    topics = extract_classification(frontmatter).get("topics") or []
    query = " ".join(str(t) for t in topics[:3]) or display_title_from_frontmatter(frontmatter)
    try:
        rows = search_books(query=query, limit=limit, book=safe_book_id(frontmatter, book_path))
    except Exception:
        return []
    passages = []
    for row in rows:
        citation = row.get("citation") or row.get("heading_path") or row.get("chunk_id")
        text = (row.get("text") or "").strip().replace("\n", " ")
        if len(text) > 280:
            text = text[:280].rstrip() + "..."
        passages.append(f"{citation}: {text}")
    return passages


def integration_table() -> str:
    return (
        "| Obsidian | OmniFocus | Calendar |\n"
        "|---|---|---|\n"
        "| Create or link notes for the book's main ideas. | Create concrete next actions from the useful ideas. | Block time for any practice that requires protected attention. |\n"
        "| Add examples, quotes and related notes as you read. | Use projects only where the book implies repeatable implementation. | Schedule review points so the book does not become passive reading. |"
    )


def render_summary_note(book_path: Path, frontmatter: dict[str, Any], summary_data: dict[str, Any]) -> str:
    title = display_title_from_frontmatter(frontmatter)
    author = display_author_from_frontmatter(frontmatter)
    core = fallback_core_thesis(frontmatter, summary_data)
    ideas = fallback_major_ideas(frontmatter, summary_data)
    questions = fallback_questions(frontmatter, summary_data)

    body = f"""# {title} — Summary

## Introduction

{core}

## Core Concepts / Ideas

{bullet_list(ideas)}

## Interconnections

Machine-draft placeholder. Review how the book's major ideas connect to each other, to other books in the corpus and to your existing systems.

## Practical Implications

{bullet_list(questions, fallback="Machine-draft placeholder. Add the situations where this book is practically useful.")}

## Integration Table

{integration_table()}

## Bottom Line / Conclusion

{core}
"""
    return textwrap.dedent(body).strip() + "\n"


def render_implementation_note(book_path: Path, frontmatter: dict[str, Any], summary_data: dict[str, Any]) -> str:
    title = display_title_from_frontmatter(frontmatter)
    ideas = fallback_major_ideas(frontmatter, summary_data)
    topics = extract_classification(frontmatter).get("topics") or []
    questions = fallback_questions(frontmatter, summary_data)

    body = f"""# {title} — Implementation Notes

## 1. Implementation Posture

Treat this book as a source of practices and operating principles, not merely as something to remember.

Most relevant themes:

{bullet_list(ideas)}

## 2. Tool-by-tool Setup

### Obsidian

- Create a note for each major concept worth keeping.
- Link this book note to related concepts, projects and topic maps.
- Capture direct citations only where they are useful for later writing or decision-making.

### OmniFocus

- Convert applicable ideas into concrete next actions.
- Avoid vague actions such as "apply this book".
- Use review projects for slow-compounding practices.

### Calendar

- Schedule practices that require protected time.
- Add review blocks for recurring systems suggested by the book.
- Do not rely on intention where time needs to be defended.

## 3. Cadence / Review Rhythm

- Daily: choose one idea to notice or practise.
- Weekly: review whether any idea has become an actual behaviour.
- Monthly: decide whether this book still belongs in active implementation.

## 4. Guardrails and Failure Modes

- Do not turn the book into slogans.
- Do not create more tasks than the ideas are worth.
- Do not confuse agreement with implementation.
- Review any advice against your own context and constraints.

## 5. Metrics and Validation Checks

Useful validation questions:

{bullet_list(questions)}

Red flags:

- The note grows but behaviour does not change.
- The book creates guilt rather than usable direction.
- The ideas remain isolated rather than connected to projects, calendar blocks or decisions.
"""
    return textwrap.dedent(body).strip() + "\n"


def render_compact_book_note(book_path: Path, frontmatter: dict[str, Any], summary_data: dict[str, Any]) -> str:
    title = display_title_from_frontmatter(frontmatter)
    author = display_author_from_frontmatter(frontmatter)
    core = fallback_core_thesis(frontmatter, summary_data)
    ideas = fallback_major_ideas(frontmatter, summary_data)
    questions = fallback_questions(frontmatter, summary_data)
    passages = useful_passages(book_path, frontmatter)

    body = f"""# {title}

Author: {author}

## Core thesis

{core}

## Key ideas

{bullet_list(ideas)}

## Useful passages

{bullet_list(passages, fallback="No indexed passages available yet. Run `bookmem ingest` and regenerate the note if needed.")}

## Related books

Machine-draft placeholder. Add related books manually or use `bookmem map-topic`.

## Questions this book can answer

{bullet_list(questions)}
"""
    return textwrap.dedent(body).strip() + "\n"


def render_note(book_path: Path, note_type: str = "book-note") -> tuple[str, dict[str, Any]]:
    frontmatter, _body = read_frontmatter_and_body(book_path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {book_path}")

    summary_data = load_existing_summary_for_book(book_path, frontmatter)
    fm = note_frontmatter(book_path, frontmatter, note_type=note_type)

    if note_type == "summary":
        body = render_summary_note(book_path, frontmatter, summary_data)
    elif note_type == "implementation-notes":
        body = render_implementation_note(book_path, frontmatter, summary_data)
    else:
        body = render_compact_book_note(book_path, frontmatter, summary_data)

    return f"---\n{yaml_dump(fm)}\n---\n\n{body}", fm


def note_output_path(book_path: Path, note_type: str = "book-note", output_dir: Path | None = None) -> Path:
    frontmatter, _body = read_frontmatter_and_body(book_path)
    if not frontmatter:
        raise ValueError(f"No frontmatter found in {book_path}")

    title = display_title_from_frontmatter(frontmatter)
    author = display_author_from_frontmatter(frontmatter)
    templates = load_note_templates()
    suffix = templates.get(note_type, {}).get("filename_suffix", "Book Note")

    filename = slugify_filename(f"{title} - {author} - {suffix}.md")
    settings = get_settings()
    target_dir = output_dir or Path("data/notes")
    return target_dir / filename


def generate_note(book_path: Path, note_type: str = "book-note", output_dir: Path | None = None, write: bool = False, overwrite: bool = False) -> tuple[Path, str]:
    content, _fm = render_note(book_path, note_type=note_type)
    target = note_output_path(book_path, note_type=note_type, output_dir=output_dir)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            raise FileExistsError(f"Note already exists: {target}")
        target.write_text(content, encoding="utf-8")
    return target, content


def generate_notes_for_directory(
    books_dir: Path,
    note_type: str = "book-note",
    output_dir: Path | None = None,
    write: bool = False,
    overwrite: bool = False,
) -> list[tuple[Path, Path]]:
    generated = []
    for path in discover_book_files(books_dir):
        try:
            target, _content = generate_note(path, note_type=note_type, output_dir=output_dir, write=write, overwrite=overwrite)
            generated.append((path, target))
        except Exception:
            continue
    return generated
