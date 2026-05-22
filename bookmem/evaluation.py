"""Retrieval benchmark/evaluation support for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Any

import yaml

from .search import search_books
from .router import route_query


EVAL_VERSION = "0.1.0"


@dataclass
class EvalQuery:
    id: str
    query: str
    expected_books: list[str]
    expected_topics: list[str]
    notes: str | None = None


def normalise(value: str | None) -> str:
    value = (value or "").lower()
    value = re.sub(r"^the\s+", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def load_eval_queries(path: Path = Path("eval/queries.yaml")) -> list[EvalQuery]:
    if not path.exists():
        raise FileNotFoundError(f"Evaluation query file not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    queries = []
    for index, item in enumerate(data.get("queries", []) or [], start=1):
        if not isinstance(item, dict):
            continue
        query = str(item.get("query") or "").strip()
        if not query:
            continue
        queries.append(
            EvalQuery(
                id=str(item.get("id") or f"query_{index}"),
                query=query,
                expected_books=[str(v) for v in item.get("expected_books", []) or []],
                expected_topics=[str(v) for v in item.get("expected_topics", []) or []],
                notes=item.get("notes"),
            )
        )
    return queries


def result_matches_expected(row: dict[str, Any], expected_books: list[str], expected_topics: list[str]) -> bool:
    title = normalise(str(row.get("title") or ""))
    author = normalise(str(row.get("author") or ""))
    primary_label = normalise(str(row.get("primary_label") or ""))
    heading_path = normalise(str(row.get("heading_path") or ""))
    text = normalise(str(row.get("text") or ""))
    haystack = " ".join([title, author, primary_label, heading_path, text])

    for book in expected_books:
        if normalise(book) and normalise(book) in title:
            return True

    for topic in expected_topics:
        topic_norm = normalise(topic)
        if topic_norm and topic_norm in haystack:
            return True

    return False


def reciprocal_rank(rows: list[dict[str, Any]], expected_books: list[str], expected_topics: list[str]) -> float:
    for idx, row in enumerate(rows, start=1):
        if result_matches_expected(row, expected_books, expected_topics):
            return 1.0 / idx
    return 0.0


def recall_at_k(rows: list[dict[str, Any]], expected_books: list[str], expected_topics: list[str], k: int) -> float:
    """Fraction of expected books/topics that have at least one match in the top-k rows."""
    expected_items = (
        [([book], []) for book in expected_books]
        + [([], [topic]) for topic in expected_topics]
    )
    if not expected_items:
        return 0.0
    top_rows = rows[:k]
    matched = sum(
        1
        for books, topics in expected_items
        if any(result_matches_expected(row, books, topics) for row in top_rows)
    )
    return matched / len(expected_items)


def evaluate_retrieval(
    query_file: Path = Path("eval/queries.yaml"),
    k: int = 5,
    limit: int | None = None,
    use_route: bool = True,
) -> dict[str, Any]:
    queries = load_eval_queries(query_file)
    limit = limit or max(k, 10)
    results = []
    failed = []
    recall_values = []
    rr_values = []

    for item in queries:
        route = {}
        class_codes = []
        aliases = []
        errors = []
        rows: list[dict[str, Any]] = []

        if use_route:
            try:
                route_obj = route_query(item.query)
                if hasattr(route_obj, "model_dump"):
                    route = route_obj.model_dump()
                elif hasattr(route_obj, "__dict__"):
                    route = dict(route_obj.__dict__)
                elif isinstance(route_obj, dict):
                    route = route_obj
                class_codes = [str(v) for v in route.get("class_codes", []) or []]
                aliases = [str(v) for v in route.get("aliases", []) or []]
            except Exception as exc:
                errors.append(f"route failed: {exc}")

        try:
            if class_codes:
                for class_code in class_codes[:3]:
                    rows.extend(search_books(query=item.query, limit=limit, class_code=[class_code]))
                    if len(rows) >= limit:
                        break
            elif aliases:
                rows.extend(search_books(query=item.query, limit=limit, alias=[aliases[0]]))
            else:
                rows.extend(search_books(query=item.query, limit=limit))
        except Exception as exc:
            errors.append(f"search failed: {exc}")

        if len(rows) < limit:
            try:
                seen = {row.get("chunk_id") for row in rows}
                fallback = search_books(query=item.query, limit=limit)
                for row in fallback:
                    if row.get("chunk_id") not in seen:
                        rows.append(row)
                    if len(rows) >= limit:
                        break
            except Exception as exc:
                errors.append(f"fallback search failed: {exc}")

        rows = rows[:limit]
        recall = recall_at_k(rows, item.expected_books, item.expected_topics, k=k)
        rr = reciprocal_rank(rows, item.expected_books, item.expected_topics)
        recall_values.append(recall)
        rr_values.append(rr)

        top_results = [
            {
                "rank": idx,
                "title": row.get("title"),
                "author": row.get("author"),
                "chunk_id": row.get("chunk_id"),
                "heading_path": row.get("heading_path"),
                "primary_class": row.get("primary_class"),
                "citation": row.get("citation"),
                "matched": result_matches_expected(row, item.expected_books, item.expected_topics),
            }
            for idx, row in enumerate(rows[:k], start=1)
        ]

        record = {
            "id": item.id,
            "query": item.query,
            "expected_books": item.expected_books,
            "expected_topics": item.expected_topics,
            "recall_at_k": recall,
            "reciprocal_rank": rr,
            "route": route,
            "top_results": top_results,
            "errors": errors,
        }
        results.append(record)

        if recall == 0.0 or errors:
            failed.append(record)

    recall_mean = sum(recall_values) / len(recall_values) if recall_values else 0.0
    mrr = sum(rr_values) / len(rr_values) if rr_values else 0.0

    return {
        "schema_version": 1,
        "eval_version": EVAL_VERSION,
        "query_file": str(query_file),
        "query_count": len(queries),
        "k": k,
        "limit": limit,
        "use_route": use_route,
        "recall_at_k": round(recall_mean, 4),
        "mrr": round(mrr, 4),
        "failed_count": len(failed),
        "failed_queries": failed,
        "results": results,
    }


def eval_queries_as_dict(queries: list[EvalQuery]) -> list[dict[str, Any]]:
    return [asdict(item) for item in queries]
