"""Deep integrity diagnostics for BookMem.

Deep doctor is intentionally diagnostic. It does not mutate data.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import random
from typing import Any

import yaml

from .doctor import STATUS_OK, STATUS_WARN, STATUS_FAIL
from .config import get_settings
from .manifest import load_manifest
from .frontmatter import discover_book_files, read_markdown_with_frontmatter
from .index_versions import indexed_table_status, manifest_index_metadata
from .embeddings import embedding_dimension


DEEP_DOCTOR_VERSION = "0.1.0"


@dataclass
class DeepCheck:
    name: str
    status: str
    message: str
    details: dict[str, Any] | None = None


def _status_from_checks(checks: list[DeepCheck]) -> str:
    if any(check.status == STATUS_FAIL for check in checks):
        return STATUS_FAIL
    if any(check.status == STATUS_WARN for check in checks):
        return STATUS_WARN
    return STATUS_OK


def _safe_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _safe_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _lancedb_rows(sample_size: int = 10) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    settings = get_settings()
    status = indexed_table_status()
    if not status.get("table_exists"):
        return [], status

    import lancedb

    db = lancedb.connect(str(settings.db_dir))
    table = db.open_table(settings.table_name)
    rows = table.to_pandas()
    if rows.empty:
        return [], status
    records = rows.to_dict(orient="records")
    rng = random.Random(42)
    sample = records if len(records) <= sample_size else rng.sample(records, sample_size)
    return sample, status


def check_sample_chunks(sample_size: int = 10) -> DeepCheck:
    try:
        rows, status = _lancedb_rows(sample_size)
        if not status.get("table_exists"):
            return DeepCheck("Sample chunks", STATUS_WARN, status.get("reason") or "No index table available.", {"index_status": status})
        if not rows:
            return DeepCheck("Sample chunks", STATUS_WARN, "No indexed chunks available to sample.", {"index_status": status})

        required = ["chunk_id", "book_id", "text", "source_path"]
        missing = []
        unreadable_sources = []
        for row in rows:
            for key in required:
                if key not in row or row.get(key) in (None, ""):
                    missing.append({"chunk_id": row.get("chunk_id"), "missing": key})
            source = row.get("source_path")
            if source and not Path(str(source)).exists():
                unreadable_sources.append({"chunk_id": row.get("chunk_id"), "source_path": source})

        if missing or unreadable_sources:
            return DeepCheck(
                "Sample chunks",
                STATUS_FAIL,
                f"{len(missing)} missing field issue(s), {len(unreadable_sources)} missing source file issue(s).",
                {"missing": missing[:50], "unreadable_sources": unreadable_sources[:50]},
            )
        return DeepCheck("Sample chunks", STATUS_OK, f"Sampled {len(rows)} chunk(s); required fields and source files look valid.")
    except Exception as exc:
        return DeepCheck("Sample chunks", STATUS_FAIL, f"Could not sample chunks: {exc}")


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def check_citations(sample_size: int = 20) -> DeepCheck:
    try:
        rows, status = _lancedb_rows(sample_size)
        if not rows:
            return DeepCheck("Citations", STATUS_WARN, "No indexed rows available for citation checks.", {"index_status": status})

        issues = []
        checked = 0
        for row in rows:
            source = row.get("source_path")
            start = row.get("start_line")
            end = row.get("end_line")
            if not source or start in (None, "") or end in (None, ""):
                issues.append({"chunk_id": row.get("chunk_id"), "issue": "missing citation source/start/end"})
                continue
            path = Path(str(source))
            if not path.exists():
                issues.append({"chunk_id": row.get("chunk_id"), "issue": "source path missing", "source_path": source})
                continue
            try:
                start_i = int(start)
                end_i = int(end)
                total = _line_count(path)
                checked += 1
                if start_i < 1 or end_i < start_i or end_i > total:
                    issues.append({
                        "chunk_id": row.get("chunk_id"),
                        "issue": "line range invalid",
                        "start_line": start_i,
                        "end_line": end_i,
                        "line_count": total,
                        "source_path": source,
                    })
            except Exception as exc:
                issues.append({"chunk_id": row.get("chunk_id"), "issue": f"line parse/read failed: {exc}"})

        if issues:
            return DeepCheck("Citations", STATUS_FAIL, f"{len(issues)} citation issue(s) found.", {"issues": issues[:50], "checked": checked})
        return DeepCheck("Citations", STATUS_OK, f"Checked {checked} sampled citation line range(s).")
    except Exception as exc:
        return DeepCheck("Citations", STATUS_FAIL, f"Citation checks failed: {exc}")


def check_manifest_paths() -> DeepCheck:
    try:
        manifest = load_manifest()
        books = manifest.get("books", []) if isinstance(manifest, dict) else []
        missing = []
        checked = 0
        for record in books:
            if not isinstance(record, dict):
                continue
            for key in ("source_path", "canonical_path"):
                value = record.get(key)
                if value:
                    checked += 1
                    if not Path(str(value)).exists():
                        missing.append({"book_id": record.get("book_id"), "field": key, "path": value})
        if missing:
            return DeepCheck("Manifest paths", STATUS_FAIL, f"{len(missing)} manifest path(s) do not exist.", {"missing": missing[:100], "checked": checked})
        return DeepCheck("Manifest paths", STATUS_OK, f"Checked {checked} manifest path reference(s).")
    except Exception as exc:
        return DeepCheck("Manifest paths", STATUS_FAIL, f"Manifest path check failed: {exc}")


def check_summaries_match_books() -> DeepCheck:
    try:
        settings = get_settings()
        book_ids = set()
        for path in discover_book_files(settings.books_dir):
            fm, _body, _had = read_markdown_with_frontmatter(path)
            book_id = fm.get("book_id")
            if book_id:
                book_ids.add(str(book_id))

        summary_root = Path("data/summaries")
        if not summary_root.exists():
            return DeepCheck("Summaries", STATUS_WARN, "data/summaries does not exist.")

        issues = []
        checked = 0
        for book_yaml in summary_root.glob("*/book.yaml"):
            checked += 1
            data = _safe_yaml(book_yaml) or {}
            folder_id = book_yaml.parent.name
            summary_id = str(data.get("book_id") or folder_id)
            if summary_id not in book_ids and folder_id not in book_ids:
                issues.append({"summary": str(book_yaml), "book_id": summary_id, "issue": "no matching canonical book_id"})
            chapters = book_yaml.parent / "chapters.yaml"
            if chapters.exists():
                chapter_data = _safe_yaml(chapters) or {}
                chapter_id = str(chapter_data.get("book_id") or summary_id)
                if chapter_id != summary_id:
                    issues.append({"summary": str(chapters), "book_id": chapter_id, "expected": summary_id, "issue": "chapter/book summary book_id mismatch"})
        if issues:
            return DeepCheck("Summaries", STATUS_WARN, f"{len(issues)} summary issue(s) found.", {"issues": issues[:100], "canonical_book_ids": len(book_ids)})
        return DeepCheck("Summaries", STATUS_OK, f"Checked {checked} book summary file(s).")
    except Exception as exc:
        return DeepCheck("Summaries", STATUS_FAIL, f"Summary check failed: {exc}")


def check_concept_source_chunks(sample_size: int = 100) -> DeepCheck:
    try:
        chunk_ids = set()
        try:
            rows, _status = _lancedb_rows(5000)
            # _lancedb_rows samples; use direct table for all where possible.
            settings = get_settings()
            import lancedb
            db = lancedb.connect(str(settings.db_dir))
            if settings.table_name in db.table_names():
                table = db.open_table(settings.table_name)
                df = table.to_pandas()
                if "chunk_id" in df.columns:
                    chunk_ids = set(str(x) for x in df["chunk_id"].dropna().tolist())
        except Exception:
            pass

        path = Path("data/concepts/concepts.json")
        if not path.exists():
            return DeepCheck("Concept source chunks", STATUS_WARN, "Concept index not found: data/concepts/concepts.json")
        data = _safe_json(path)
        concepts = data.get("concepts", []) if isinstance(data, dict) else []
        issues = []
        checked = 0
        for concept in concepts[:sample_size]:
            if not isinstance(concept, dict):
                continue
            for src in concept.get("source_chunks", []) or []:
                checked += 1
                if isinstance(src, dict):
                    chunk_id = src.get("chunk_id")
                else:
                    chunk_id = str(src)
                if chunk_id and chunk_ids and str(chunk_id) not in chunk_ids:
                    issues.append({"concept_id": concept.get("concept_id"), "chunk_id": chunk_id})
        if issues:
            return DeepCheck("Concept source chunks", STATUS_WARN, f"{len(issues)} concept source chunk reference(s) missing from index.", {"issues": issues[:100], "checked": checked})
        if not chunk_ids:
            return DeepCheck("Concept source chunks", STATUS_WARN, "Could not load index chunk IDs; concept references were only syntax-checked.", {"checked": checked})
        return DeepCheck("Concept source chunks", STATUS_OK, f"Checked {checked} concept source chunk reference(s).")
    except Exception as exc:
        return DeepCheck("Concept source chunks", STATUS_FAIL, f"Concept source chunk check failed: {exc}")


def check_graph_nodes() -> DeepCheck:
    try:
        path = Path("data/graphs/book_graph.json")
        if not path.exists():
            return DeepCheck("Graph", STATUS_WARN, "Book graph not found: data/graphs/book_graph.json")
        graph = _safe_json(path)
        nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
        book_ids = set()
        paths = set()
        settings = get_settings()
        for book_path in discover_book_files(settings.books_dir):
            fm, _body, _had = read_markdown_with_frontmatter(book_path)
            if fm.get("book_id"):
                book_ids.add(str(fm["book_id"]))
            paths.add(str(book_path))

        issues = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("book_id") or "")
            node_path = str(node.get("path") or "")
            if node_id and node_id not in book_ids and node_path not in paths:
                issues.append({"book_id": node_id, "path": node_path})
            elif node_path and not Path(node_path).exists():
                issues.append({"book_id": node_id, "path": node_path, "issue": "path missing"})
        if issues:
            return DeepCheck("Graph", STATUS_WARN, f"{len(issues)} graph node(s) do not reference known books.", {"issues": issues[:100]})
        return DeepCheck("Graph", STATUS_OK, f"Checked {len(nodes)} graph node(s).")
    except Exception as exc:
        return DeepCheck("Graph", STATUS_FAIL, f"Graph check failed: {exc}")


def check_embedding_dimension() -> DeepCheck:
    try:
        current_dim = embedding_dimension()
        stored = manifest_index_metadata()
        stored_dim = stored.get("embedding_dimension")
        status = indexed_table_status()
        details = {"current_dimension": current_dim, "stored_dimension": stored_dim, "index_status": status}

        vector_dim = None
        try:
            settings = get_settings()
            import lancedb
            db = lancedb.connect(str(settings.db_dir))
            if settings.table_name in db.table_names():
                table = db.open_table(settings.table_name)
                df = table.to_pandas()
                if not df.empty and "vector" in df.columns:
                    first = df["vector"].dropna().iloc[0]
                    vector_dim = len(first)
                    details["lancedb_vector_dimension"] = vector_dim
        except Exception as exc:
            details["lancedb_vector_dimension_error"] = str(exc)

        mismatches = []
        if current_dim and stored_dim and int(stored_dim) != int(current_dim):
            mismatches.append(f"stored={stored_dim}, current={current_dim}")
        if current_dim and vector_dim and int(vector_dim) != int(current_dim):
            mismatches.append(f"lancedb={vector_dim}, current={current_dim}")
        if mismatches:
            return DeepCheck("Embedding dimension", STATUS_FAIL, "Embedding dimension mismatch: " + "; ".join(mismatches), details)
        if not current_dim:
            return DeepCheck("Embedding dimension", STATUS_WARN, "Current embedding dimension could not be determined.", details)
        return DeepCheck("Embedding dimension", STATUS_OK, f"Embedding dimension looks consistent: {current_dim}.", details)
    except Exception as exc:
        return DeepCheck("Embedding dimension", STATUS_FAIL, f"Embedding dimension check failed: {exc}")


def check_review_queue_parse() -> DeepCheck:
    try:
        root = Path("data/review")
        if not root.exists():
            return DeepCheck("Review queues", STATUS_WARN, "data/review does not exist.")
        issues = []
        checked = 0
        for path in sorted(list(root.glob("*.yaml")) + list(root.glob("*.yml")) + list(root.glob("*.json"))):
            checked += 1
            try:
                if path.suffix.lower() == ".json":
                    _safe_json(path)
                else:
                    _safe_yaml(path)
            except Exception as exc:
                issues.append({"path": str(path), "error": str(exc)})
        if issues:
            return DeepCheck("Review queues", STATUS_FAIL, f"{len(issues)} review queue file(s) failed to parse.", {"issues": issues})
        return DeepCheck("Review queues", STATUS_OK, f"Parsed {checked} review queue file(s).")
    except Exception as exc:
        return DeepCheck("Review queues", STATUS_FAIL, f"Review queue check failed: {exc}")


def check_config_schema_parse() -> DeepCheck:
    try:
        roots = [Path("config"), Path("config/profiles")]
        issues = []
        checked = 0
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(list(root.glob("*.yaml")) + list(root.glob("*.yml")) + list(root.glob("*.json"))):
                checked += 1
                try:
                    if path.suffix.lower() == ".json":
                        _safe_json(path)
                    else:
                        data = _safe_yaml(path)
                        if data is None:
                            issues.append({"path": str(path), "issue": "empty file"})
                        elif not isinstance(data, (dict, list)):
                            issues.append({"path": str(path), "issue": "top-level value is not mapping/list"})
                except Exception as exc:
                    issues.append({"path": str(path), "error": str(exc)})
        if issues:
            return DeepCheck("Config schema parse", STATUS_FAIL, f"{len(issues)} config file issue(s).", {"issues": issues[:100]})
        return DeepCheck("Config schema parse", STATUS_OK, f"Parsed {checked} config file(s).")
    except Exception as exc:
        return DeepCheck("Config schema parse", STATUS_FAIL, f"Config schema parse check failed: {exc}")


def run_deep_doctor(sample_size: int = 10) -> dict[str, Any]:
    checks = [
        check_sample_chunks(sample_size=sample_size),
        check_citations(sample_size=max(sample_size, 20)),
        check_manifest_paths(),
        check_summaries_match_books(),
        check_concept_source_chunks(sample_size=max(sample_size * 10, 100)),
        check_graph_nodes(),
        check_embedding_dimension(),
        check_review_queue_parse(),
        check_config_schema_parse(),
    ]
    status = _status_from_checks(checks)
    reasons = [f"{check.name}: {check.message}" for check in checks if check.status != STATUS_OK]
    return {
        "deep_doctor_version": DEEP_DOCTOR_VERSION,
        "status": status,
        "checks": [asdict(check) for check in checks],
        "reasons": reasons,
    }
