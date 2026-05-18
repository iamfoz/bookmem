"""Optional LLM-assisted summary providers for BookMem."""

from __future__ import annotations

from pathlib import Path
import json
import os
import re
from typing import Any

import requests
import yaml

from .chunking import parse_frontmatter, split_by_markdown_headings
from .summaries import (
    SUMMARY_SCHEMA_VERSION,
    SUMMARY_GENERATOR_VERSION,
    _book_metadata,
    _chapter_summaries,
    _first_substantial_paragraph,
    _heading_ideas,
    _best_for,
    _keyword_candidates,
    summaries_root,
    utc_now_iso,
)
from .manifest import get_record_for_path, markdown_hashes, relative_or_absolute, upsert_book_record


SUMMARY_PROVIDER_VERSION = "0.1.0"


def load_summary_providers() -> dict[str, Any]:
    providers: dict[str, Any] = {}
    base = Path("config/summary_providers.yaml")
    if base.exists():
        data = yaml.safe_load(base.read_text(encoding="utf-8")) or {}
        providers.update(data.get("summary_providers", {}))

    custom_dir = Path("config/summary_providers.d")
    if custom_dir.exists():
        for path in sorted(custom_dir.glob("*.y*ml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            providers.update(data.get("summary_providers", {}))

    if "deterministic" not in providers:
        providers["deterministic"] = {"enabled": True, "generator": "deterministic_extract", "model": None}

    return providers


def validate_summary_providers() -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    providers = load_summary_providers()
    for name, cfg in providers.items():
        if not isinstance(cfg, dict):
            issues.append({"provider": name, "issue": "invalid_provider", "message": "Provider must be a mapping."})
            continue
        if "enabled" in cfg and not isinstance(cfg["enabled"], bool):
            issues.append({"provider": name, "issue": "invalid_enabled", "message": "enabled must be true or false."})
        if name in {"openai", "local_ollama"} and not cfg.get("model"):
            issues.append({"provider": name, "issue": "missing_model", "message": "LLM provider needs a model."})
    return issues


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "\n\n[TRUNCATED FOR SUMMARY PROVIDER]"


def _summary_prompt(meta: dict[str, Any], body: str) -> str:
    title = meta.get("title") or "Untitled"
    author = meta.get("author") or "Unknown author"
    return f"""
You are generating a machine-draft BookMem summary for a Markdown book.

Return strict JSON only, with this shape:
{{
  "core_thesis": "one concise paragraph",
  "major_ideas": ["idea 1", "idea 2"],
  "best_for_questions_about": ["topic 1", "topic 2"],
  "keywords": ["keyword 1", "keyword 2"],
  "chapters": [
{{
  "title": "Chapter title",
  "summary": "concise chapter summary",
  "major_ideas": ["idea"],
  "headings": ["heading"],
  "keywords": ["keyword"]
}}
  ]
}}

Rules:
- Do not claim human review.
- Be faithful to the supplied text.
- Prefer practical, retrieval-friendly phrasing.
- Keep the output useful for search and agent routing.

Title: {title}
Author: {author}

BOOK TEXT:
{body}
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _call_openai(prompt: str, cfg: dict[str, Any]) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError("OpenAI provider requires the `openai` package.") from exc

    api_key_env = cfg.get("api_key_env") or "OPENAI_API_KEY"
    if not os.getenv(api_key_env):
        raise RuntimeError(f"OpenAI provider is enabled but {api_key_env} is not set.")

    client = OpenAI(api_key=os.getenv(api_key_env))
    model = cfg.get("model") or "gpt-5.5-thinking"
    # Use Chat Completions for broad SDK compatibility.
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=float(cfg.get("temperature", 0.2)),
    )
    content = response.choices[0].message.content or "{}"
    return _extract_json(content)


def _call_ollama(prompt: str, cfg: dict[str, Any]) -> dict[str, Any]:
    base_url = str(cfg.get("base_url") or "http://localhost:11434").rstrip("/")
    model = cfg.get("model") or "qwen3"
    response = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": float(cfg.get("temperature", 0.2))},
        },
        timeout=int(cfg.get("timeout", 300)),
    )
    response.raise_for_status()
    data = response.json()
    return _extract_json(data.get("response") or "{}")


def _deterministic_payload(path: Path, meta: dict[str, Any], body: str, book_meta: dict[str, Any], sections: list[tuple[str, str]]) -> dict[str, Any]:
    combined_text = "\n\n".join(section_text for _heading, section_text in sections) or body
    ideas = _heading_ideas(sections, book_meta["topics"], limit=12)
    best_for = _best_for(book_meta, ideas, combined_text, limit=10)
    return {
        "core_thesis": _first_substantial_paragraph(combined_text, max_chars=750),
        "major_ideas": ideas,
        "best_for_questions_about": best_for,
        "keywords": _keyword_candidates(combined_text, limit=20),
        "chapters": _chapter_summaries(sections),
    }


def summarise_book_with_provider(
    path: Path,
    provider: str = "deterministic",
    write: bool = True,
    overwrite: bool = True,
):
    from .summaries import SummaryResult

    providers = load_summary_providers()
    if provider not in providers:
        raise KeyError(f"Unknown summary provider: {provider}")

    cfg = providers[provider] or {}
    if not cfg.get("enabled", False) and provider != "deterministic":
        raise RuntimeError(f"Summary provider `{provider}` is disabled in config/summary_providers.yaml.")

    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(raw)
    book_meta = _book_metadata(path, meta)
    sections = split_by_markdown_headings(body)
    combined_text = "\n\n".join(section_text for _heading, section_text in sections) or body

    if provider == "deterministic":
        provider_payload = _deterministic_payload(path, meta, body, book_meta, sections)
        generator = "deterministic"
        model = cfg.get("model")
    else:
        max_chars = int(cfg.get("max_input_chars") or 120000)
        prompt = _summary_prompt(book_meta, _truncate(combined_text, max_chars=max_chars))
        if provider == "openai":
            provider_payload = _call_openai(prompt, cfg)
        elif provider in {"local_ollama", "ollama"}:
            provider_payload = _call_ollama(prompt, cfg)
        else:
            raise RuntimeError(f"Provider `{provider}` has no runner.")
        generator = str(cfg.get("generator") or provider)
        model = cfg.get("model")

    generated_at = utc_now_iso()
    book_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generator_version": SUMMARY_PROVIDER_VERSION if provider != "deterministic" else SUMMARY_GENERATOR_VERSION,
        "generated_at": generated_at,
        "book_id": book_meta["book_id"],
        "title": book_meta["title"],
        "author": book_meta["author"],
        "source_path": relative_or_absolute(path),
        "classification": {
            "scheme": "BMDC",
            "primary_class": book_meta["primary_class"],
            "primary_label": book_meta["primary_label"],
            "secondary_classes": book_meta["secondary_classes"],
            "routing_aliases": book_meta["routing_aliases"],
            "topics": book_meta["topics"],
        },
        "core_thesis": provider_payload.get("core_thesis") or "",
        "major_ideas": provider_payload.get("major_ideas") or [],
        "best_for_questions_about": provider_payload.get("best_for_questions_about") or [],
        "keywords": provider_payload.get("keywords") or [],
        "chapter_count": len(provider_payload.get("chapters") or []),
        "summary_kind": "llm_assisted" if provider != "deterministic" else "deterministic_extract",
        "generator": generator,
        "provider": provider,
        "model": model,
        "review_status": "machine_draft",
    }

    chapters = provider_payload.get("chapters") or []
    chapter_summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "generator_version": book_summary["generator_version"],
        "generated_at": generated_at,
        "book_id": book_meta["book_id"],
        "title": book_meta["title"],
        "author": book_meta["author"],
        "source_path": relative_or_absolute(path),
        "generator": generator,
        "provider": provider,
        "model": model,
        "review_status": "machine_draft",
        "chapters": chapters,
    }

    out_dir = summaries_root() / book_meta["book_id"]
    book_path = out_dir / "book.yaml"
    chapters_path = out_dir / "chapters.yaml"
    written = False

    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        if overwrite or not book_path.exists():
            book_path.write_text(yaml.safe_dump(book_summary, sort_keys=False, allow_unicode=True), encoding="utf-8")
        if overwrite or not chapters_path.exists():
            chapters_path.write_text(yaml.safe_dump(chapter_summary, sort_keys=False, allow_unicode=True), encoding="utf-8")
        written = True

        content_hash, frontmatter_hash, full_hash = markdown_hashes(path)
        existing = get_record_for_path(path) or {}
        upsert_book_record(
            {
                **existing,
                "book_id": book_meta["book_id"],
                "canonical_path": relative_or_absolute(path),
                "content_hash": content_hash,
                "frontmatter_hash": frontmatter_hash,
                "full_hash": full_hash,
                "last_summarised": generated_at,
                "summary_path": relative_or_absolute(book_path),
                "chapter_summary_path": relative_or_absolute(chapters_path),
                "summary_generator_version": book_summary["generator_version"],
                "summary_provider": provider,
                "summary_model": model,
                "chapter_count": len(chapters),
            }
        )

    return SummaryResult(
        book_id=book_meta["book_id"],
        title=book_meta["title"],
        author=book_meta["author"],
        summary_dir=out_dir,
        book_summary_path=book_path,
        chapter_summary_path=chapters_path,
        chapter_count=len(chapters),
        written=written,
    )


def summarise_books_with_provider(root: Path, provider: str = "deterministic", write: bool = True, overwrite: bool = True):
    files = sorted(root.glob("**/*.md"))
    return [summarise_book_with_provider(path, provider=provider, write=write, overwrite=overwrite) for path in files]
