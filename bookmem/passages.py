"""Quote extraction and commonplace-book support for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

import yaml

from .frontmatter import read_markdown_with_frontmatter
from .chunking import slugify
from .search import search_books, read_chunk
from .audit import append_audit_record


PASSAGES_VERSION = "0.1.0"
PASSAGES_DIR = Path("data/passages")
EXTRACTED_PATH = PASSAGES_DIR / "extracted.yaml"
FAVOURITES_PATH = PASSAGES_DIR / "favourites.yaml"


@dataclass
class Passage:
    passage_id: str
    quote: str
    summary: str
    why_it_matters: str
    source_chunk: str | None
    citation: str | None
    tags: list[str]
    review_status: str
    title: str | None = None
    author: str | None = None
    book_id: str | None = None
    source_path: str | None = None
    heading_path: str | None = None
    created_at: str | None = None
    favourite: bool = False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_files() -> None:
    PASSAGES_DIR.mkdir(parents=True, exist_ok=True)
    for path in (EXTRACTED_PATH, FAVOURITES_PATH):
        if not path.exists():
            path.write_text("schema_version: 1\npassages: []\n", encoding="utf-8")


def load_passage_file(path: Path) -> dict[str, Any]:
    ensure_files()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("schema_version", 1)
    data.setdefault("passages", [])
    return data


def save_passage_file(path: Path, data: dict[str, Any]) -> None:
    PASSAGES_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8")


def clean_quote(text: str, max_chars: int = 900) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].strip()


def summarise_quote(quote: str) -> str:
    words = quote.split()
    if len(words) <= 28:
        return quote
    return " ".join(words[:28]).rstrip(".,;:") + "..."


def why_quote_matters(quote: str, tags: list[str]) -> str:
    if tags:
        return f"Relevant to {', '.join(tags[:4])}."
    return "Potentially useful passage for later synthesis or citation."


def candidate_passages_from_body(body: str, limit: int = 20) -> list[dict[str, Any]]:
    """Deterministically extract plausible quotable passages.

    This is intentionally conservative: it favours complete paragraphs,
    avoids very short fragments and does not claim human curation.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    candidates = []
    for idx, para in enumerate(paragraphs):
        plain = re.sub(r"^#{1,6}\s+", "", para, flags=re.M)
        plain = re.sub(r"\[[^\]]+\]\([^\)]*\)", "", plain)
        plain = re.sub(r"[*_`>#]+", "", plain)
        words = re.findall(r"\b\w+(?:['’\-]\w+)?\b", plain)
        if len(words) < 25 or len(words) > 180:
            continue
        score = 0
        lowered = plain.lower()
        for term in ("important", "therefore", "because", "principle", "system", "habit", "risk", "value", "strategy", "model", "means that"):
            if term in lowered:
                score += 1
        if re.search(r"[:;]", plain):
            score += 1
        candidates.append({"index": idx, "quote": clean_quote(plain), "score": score, "word_count": len(words)})
    candidates.sort(key=lambda item: (-item["score"], item["index"]))
    return candidates[:limit]


def extract_passages(book_path: Path, limit: int = 20, tag: list[str] | None = None, write: bool = True) -> dict[str, Any]:
    frontmatter, body, _had = read_markdown_with_frontmatter(book_path)
    title = str(frontmatter.get("title") or book_path.stem)
    author = str(frontmatter.get("author") or "") or None
    book_id = str(frontmatter.get("book_id") or slugify(f"{author or ''}_{title}"))
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    tags = tag or [str(t) for t in (classification.get("topics") or [])[:5]]
    candidates = candidate_passages_from_body(body, limit=limit)

    passages = []
    for idx, cand in enumerate(candidates, start=1):
        passage_id = slugify(f"{book_id}_{idx}_{cand['quote'][:40]}")
        citation = f"{title}" + (f" — {author}" if author else "")
        p = Passage(
            passage_id=passage_id,
            quote=cand["quote"],
            summary=summarise_quote(cand["quote"]),
            why_it_matters=why_quote_matters(cand["quote"], tags),
            source_chunk=None,
            citation=citation,
            tags=tags,
            review_status="machine_draft",
            title=title,
            author=author,
            book_id=book_id,
            source_path=str(book_path),
            heading_path=None,
            created_at=utc_now_iso(),
            favourite=False,
        )
        passages.append(asdict(p))

    if write:
        data = load_passage_file(EXTRACTED_PATH)
        existing = data.get("passages", [])
        existing_ids = {item.get("passage_id") for item in existing if isinstance(item, dict)}
        added = []
        for passage in passages:
            if passage["passage_id"] not in existing_ids:
                existing.append(passage)
                added.append(passage)
        data["passages"] = existing
        data["updated_at"] = utc_now_iso()
        data["passages_version"] = PASSAGES_VERSION
        save_passage_file(EXTRACTED_PATH, data)
        append_audit_record(
            action="passages.extract",
            status="ok",
            changed_files=[EXTRACTED_PATH],
            target=str(book_path),
            message=f"Extracted {len(added)} passage(s)",
            details={"book": str(book_path), "added": len(added), "candidates": len(passages)},
        )
    else:
        added = passages

    return {"book": str(book_path), "count": len(passages), "passages": passages, "wrote": write}


def all_passages() -> list[dict[str, Any]]:
    extracted = load_passage_file(EXTRACTED_PATH).get("passages", [])
    favourites = load_passage_file(FAVOURITES_PATH).get("passages", [])
    by_id: dict[str, dict[str, Any]] = {}
    for item in extracted + favourites:
        if isinstance(item, dict):
            by_id[str(item.get("passage_id"))] = item
    return list(by_id.values())


def search_passages(query: str, limit: int = 20) -> list[dict[str, Any]]:
    q_terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
    rows = []
    for passage in all_passages():
        haystack = " ".join(
            str(passage.get(key) or "")
            for key in ("quote", "summary", "why_it_matters", "citation", "title", "author", "heading_path")
        ).lower()
        haystack += " " + " ".join(str(t).lower() for t in passage.get("tags", []) or [])
        score = sum(1 for term in q_terms if term in haystack)
        if query.lower() in haystack:
            score += 3
        if score:
            rows.append({**passage, "score": score})
    rows.sort(key=lambda item: (-item["score"], item.get("title") or ""))
    if rows:
        return rows[:limit]

    # Fallback to corpus search and convert top chunks to passage-like rows.
    fallback = []
    for row in search_books(query, limit=limit):
        quote = clean_quote(row.get("text") or row.get("excerpt") or "")
        fallback.append({
            "passage_id": row.get("chunk_id"),
            "quote": quote,
            "summary": summarise_quote(quote),
            "why_it_matters": "Retrieved from corpus search; not yet curated.",
            "source_chunk": row.get("chunk_id"),
            "citation": row.get("citation"),
            "tags": [],
            "review_status": "machine_draft",
            "title": row.get("title"),
            "author": row.get("author"),
            "book_id": row.get("book_id"),
            "source_path": row.get("source_path"),
            "heading_path": row.get("heading_path"),
            "favourite": False,
            "score": 0,
        })
    return fallback


def favourite_passage(chunk_or_passage_id: str, tags: list[str] | None = None, note: str | None = None) -> dict[str, Any]:
    ensure_files()
    passage = None
    for item in all_passages():
        if str(item.get("passage_id")) == chunk_or_passage_id or str(item.get("source_chunk")) == chunk_or_passage_id:
            passage = dict(item)
            break

    if passage is None:
        # Try treating it as a chunk id.
        row = read_chunk(chunk_or_passage_id)
        quote = clean_quote(row.get("text") or "")
        passage = {
            "passage_id": slugify(f"fav_{chunk_or_passage_id}"),
            "quote": quote,
            "summary": summarise_quote(quote),
            "why_it_matters": note or "Favourited from a retrieved chunk.",
            "source_chunk": chunk_or_passage_id,
            "citation": row.get("citation"),
            "tags": tags or [],
            "review_status": "machine_draft",
            "title": row.get("title"),
            "author": row.get("author"),
            "book_id": row.get("book_id"),
            "source_path": row.get("source_path"),
            "heading_path": row.get("heading_path"),
            "created_at": utc_now_iso(),
            "favourite": True,
        }

    passage["favourite"] = True
    if tags:
        existing_tags = passage.get("tags") or []
        passage["tags"] = sorted(set([str(t) for t in existing_tags] + [str(t) for t in tags]))
    if note:
        passage["why_it_matters"] = note
    passage.setdefault("created_at", utc_now_iso())

    data = load_passage_file(FAVOURITES_PATH)
    favs = [item for item in data.get("passages", []) if isinstance(item, dict)]
    favs = [item for item in favs if item.get("passage_id") != passage.get("passage_id")]
    favs.append(passage)
    data["passages"] = favs
    data["updated_at"] = utc_now_iso()
    data["passages_version"] = PASSAGES_VERSION
    save_passage_file(FAVOURITES_PATH, data)

    append_audit_record(
        action="passages.favourite",
        status="ok",
        changed_files=[FAVOURITES_PATH],
        target=chunk_or_passage_id,
        message="Favourited passage",
        details={"passage_id": passage.get("passage_id"), "source_chunk": passage.get("source_chunk")},
    )

    return passage


def export_passages(export_format: str = "obsidian", output: Path | None = None, favourites_only: bool = False) -> str:
    rows = load_passage_file(FAVOURITES_PATH).get("passages", []) if favourites_only else all_passages()
    fmt = export_format.lower()
    if fmt == "jsonl":
        text = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else "")
    elif fmt in {"yaml", "yml"}:
        text = yaml.safe_dump({"schema_version": 1, "passages": rows}, sort_keys=False, allow_unicode=True, width=100)
    elif fmt in {"obsidian", "markdown", "md"}:
        text = render_obsidian_passages(rows)
    else:
        raise ValueError(f"Unsupported passage export format: {export_format}")

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        append_audit_record(
            action="passages.export",
            status="ok",
            changed_files=[output],
            target=export_format,
            message=f"Exported passages as {export_format}",
            details={"count": len(rows), "favourites_only": favourites_only},
        )
    return text


def render_obsidian_passages(rows: list[dict[str, Any]]) -> str:
    lines = [
        "---",
        "type: commonplace-book",
        f"generated_at: {utc_now_iso()}",
        f"passage_count: {len(rows)}",
        "---",
        "",
        "# Commonplace Book",
        "",
    ]
    for row in rows:
        title = row.get("title") or "Untitled"
        author = row.get("author") or "Unknown author"
        lines += [
            f"## {title}",
            "",
            f"**Author:** {author}",
            f"**Citation:** {row.get('citation') or ''}",
            f"**Review status:** {row.get('review_status') or ''}",
            "",
            "> " + str(row.get("quote") or "").replace("\n", "\n> "),
            "",
            f"**Summary:** {row.get('summary') or ''}",
            "",
            f"**Why it matters:** {row.get('why_it_matters') or ''}",
            "",
        ]
        tags = row.get("tags") or []
        if tags:
            lines.append("**Tags:** " + ", ".join(f"#{str(tag).replace(' ', '-')}" for tag in tags))
            lines.append("")
        if row.get("source_chunk"):
            lines.append(f"**Source chunk:** `{row.get('source_chunk')}`")
            lines.append("")
    return "\n".join(lines)


def passage_as_dict(passage: Passage) -> dict[str, Any]:
    return asdict(passage)
