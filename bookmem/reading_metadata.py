"""Infer and manage reading metadata for BookMem books."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any


from .frontmatter import read_markdown_with_frontmatter, write_markdown_with_frontmatter
from .audit import append_audit_record


READING_METADATA_VERSION = "0.1.0"

DIFFICULTIES = {"beginner", "intermediate", "advanced"}
DENSITIES = {"light", "medium", "dense"}
BEST_READ_AS = {"cover_to_cover", "reference", "skim_then_search"}


@dataclass
class ReadingMetadataResult:
    path: str
    wrote_file: bool
    difficulty: str
    estimated_pages: int
    estimated_reading_hours: float
    density: str
    best_read_as: str
    word_count: int
    heading_count: int
    average_sentence_words: float
    confidence: str
    review_status: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def strip_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^\)]*\)", " ", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"[*_>#\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+(?:['’\-]\w+)?\b", strip_markdown(text)))


def heading_count(text: str) -> int:
    return len(re.findall(r"^#{1,6}\s+", text, flags=re.M))


def average_sentence_words(text: str) -> float:
    plain = strip_markdown(text)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if s.strip()]
    if not sentences:
        return 0.0
    counts = [len(re.findall(r"\b\w+(?:['’\-]\w+)?\b", sentence)) for sentence in sentences]
    counts = [c for c in counts if c]
    if not counts:
        return 0.0
    return round(sum(counts) / len(counts), 1)


def infer_density(words: int, avg_sentence: float, headings: int) -> str:
    heading_ratio = headings / max(words / 10000, 1)
    if avg_sentence >= 28 or (words > 90000 and heading_ratio < 5):
        return "dense"
    if avg_sentence <= 18 and heading_ratio >= 8:
        return "light"
    return "medium"


def infer_difficulty(frontmatter: dict[str, Any], body: str, density: str, avg_sentence: float) -> str:
    title = str(frontmatter.get("title") or "").lower()
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    topics = " ".join(str(t).lower() for t in classification.get("topics", []) or [])
    text = f"{title} {topics}"

    beginner_terms = ["beginner", "introduction", "introductory", "basics", "simple", "starter", "for dummies"]
    advanced_terms = ["advanced", "technical", "quantitative", "mathematical", "academic", "theory", "research"]

    if any(term in text for term in beginner_terms):
        return "beginner"
    if any(term in text for term in advanced_terms):
        return "advanced"
    if density == "dense" or avg_sentence >= 30:
        return "advanced"
    if density == "light" and avg_sentence <= 18:
        return "beginner"
    return "intermediate"


def infer_best_read_as(frontmatter: dict[str, Any], body: str, headings: int, words: int) -> str:
    title = str(frontmatter.get("title") or "").lower()
    classification = frontmatter.get("classification") if isinstance(frontmatter.get("classification"), dict) else {}
    topics = " ".join(str(t).lower() for t in classification.get("topics", []) or [])
    text = f"{title} {topics}"

    if any(term in text for term in ["dictionary", "encyclopedia", "reference", "manual", "handbook", "guidebook"]):
        return "reference"
    if headings > 80 or headings / max(words / 10000, 1) > 14:
        return "skim_then_search"
    return "cover_to_cover"


def infer_reading_metadata(path: Path, write: bool = False, overwrite: bool = False) -> ReadingMetadataResult:
    frontmatter, body, _had = read_markdown_with_frontmatter(path)
    words = word_count(body)
    headings = heading_count(body)
    avg_sentence = average_sentence_words(body)

    pages = max(1, round(words / 275)) if words else 0
    hours = round(words / 15000, 1) if words else 0.0
    density = infer_density(words, avg_sentence, headings)
    difficulty = infer_difficulty(frontmatter, body, density, avg_sentence)
    best_read_as = infer_best_read_as(frontmatter, body, headings, words)

    confidence = "medium"
    if words < 2000:
        confidence = "low"
    elif words > 15000:
        confidence = "medium"

    existing = frontmatter.get("reading") if isinstance(frontmatter.get("reading"), dict) else {}
    wrote = False

    if write:
        if existing and not overwrite and existing.get("review_status") == "human_reviewed":
            wrote = False
        elif existing and not overwrite and any(existing.get(key) for key in ("difficulty", "estimated_pages", "estimated_reading_hours", "density", "best_read_as")):
            wrote = False
        else:
            frontmatter["reading"] = {
                **existing,
                "difficulty": difficulty,
                "estimated_pages": pages,
                "estimated_reading_hours": hours,
                "density": density,
                "best_read_as": best_read_as,
                "word_count": words,
                "heading_count": headings,
                "average_sentence_words": avg_sentence,
                "inferred_at": utc_now_iso(),
                "inference_source": "deterministic",
                "confidence": confidence,
                "review_status": "machine_draft",
                "reading_metadata_version": READING_METADATA_VERSION,
            }
            write_markdown_with_frontmatter(path, frontmatter, body)
            append_audit_record(
                action="reading_metadata.infer",
                status="ok",
                changed_files=[path],
                target=str(path),
                message="Inferred reading metadata",
                details={"overwrite": overwrite, "difficulty": difficulty, "density": density, "best_read_as": best_read_as},
            )
            wrote = True

    return ReadingMetadataResult(
        path=str(path),
        wrote_file=wrote,
        difficulty=str(existing.get("difficulty") or difficulty),
        estimated_pages=int(existing.get("estimated_pages") or pages),
        estimated_reading_hours=float(existing.get("estimated_reading_hours") or hours),
        density=str(existing.get("density") or density),
        best_read_as=str(existing.get("best_read_as") or best_read_as),
        word_count=int(existing.get("word_count") or words),
        heading_count=int(existing.get("heading_count") or headings),
        average_sentence_words=float(existing.get("average_sentence_words") or avg_sentence),
        confidence=str(existing.get("confidence") or confidence),
        review_status=str(existing.get("review_status") or "machine_draft"),
    )


def reading_metadata_from_frontmatter(frontmatter: dict[str, Any]) -> dict[str, Any]:
    reading = frontmatter.get("reading")
    return reading if isinstance(reading, dict) else {}


def result_as_dict(result: ReadingMetadataResult) -> dict[str, Any]:
    return asdict(result)
