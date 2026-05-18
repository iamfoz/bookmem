from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import re
from typing import Any

from .taxonomy import get_class_label, load_taxonomy, normalise_alias, resolve_alias


ROUTER_VERSION = "0.1.0"


@dataclass
class RouteResult:
    query: str
    aliases: list[str]
    class_codes: list[str]
    confidence: float
    reason: str
    matched_terms: list[str]
    router_version: str = ROUTER_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# Extra domain phrases that are useful for routing questions before full retrieval.
# Keep these as original BookMem terms, not copied catalogue prose.
ROUTING_HINTS: dict[str, dict[str, Any]] = {
    "finance": {
        "aliases": ["finance", "investing"],
        "class_codes": ["332", "330"],
        "terms": [
            "compound interest", "interest rate", "portfolio", "asset allocation",
            "index fund", "stock market", "shares", "bonds", "etf", "pension",
            "isa", "sipp", "wealth", "net worth", "financial freedom", "money",
            "invest", "investment", "dividend", "mortgage", "inflation", "cashflow", "risk", "market crash", "financial risk",
        ],
        "reason": "The query concerns money, investing, financial markets or personal finance.",
    },
    "productivity": {
        "aliases": ["productivity", "personal_development"],
        "class_codes": ["158", "153", "650"],
        "terms": [
            "productivity", "focus", "deep work", "habits", "habit", "routine",
            "morning routine", "systems", "goals", "discipline", "procrastination",
            "time management", "energy", "motivation", "self improvement", "success",
        ],
        "reason": "The query concerns habits, focus, personal systems or self-improvement.",
    },
    "business": {
        "aliases": ["business"],
        "class_codes": ["338", "650", "658"],
        "terms": [
            "business", "startup", "entrepreneur", "entrepreneurship", "company",
            "management", "leadership", "strategy", "operations", "sales", "marketing",
            "customers", "pricing", "profit", "growth", "negotiation", "risk",
        ],
        "reason": "The query concerns business, management, entrepreneurship or commercial strategy.",
    },
    "psychology": {
        "aliases": ["psychology"],
        "class_codes": ["150", "153", "155", "158"],
        "terms": [
            "psychology", "behaviour", "behavior", "cognition", "decision making",
            "bias", "emotion", "personality", "attention", "memory", "thinking",
            "mental model", "belief", "identity", "risk",
        ],
        "reason": "The query concerns behaviour, thinking, attention or psychological patterns.",
    },
    "health": {
        "aliases": ["health"],
        "class_codes": ["610", "613"],
        "terms": [
            "health", "sleep", "nutrition", "exercise", "fitness", "diet", "stress",
            "recovery", "wellbeing", "supplements", "energy", "mental health",
        ],
        "reason": "The query concerns health, sleep, nutrition, exercise or wellbeing.",
    },
    "technology": {
        "aliases": ["technology"],
        "class_codes": ["000", "003", "004", "005", "006"],
        "terms": [
            "technology", "software", "programming", "code", "database", "ai", "agent",
            "automation", "machine learning", "computer", "systems", "infrastructure",
        ],
        "reason": "The query concerns computing, software, AI, automation or technical systems.",
    },
    "education": {
        "aliases": ["education"],
        "class_codes": ["370", "371"],
        "terms": [
            "education", "school", "teaching", "learning", "student", "classroom",
            "curriculum", "send", "ehcp", "child development",
        ],
        "reason": "The query concerns education, learning, school systems or teaching.",
    },
    "creativity": {
        "aliases": ["creativity"],
        "class_codes": ["700", "780", "800", "808"],
        "terms": [
            "creativity", "creative", "writing", "story", "storytelling", "music",
            "songwriting", "art", "design", "publishing", "rhetoric",
        ],
        "reason": "The query concerns writing, music, art, creativity or storytelling.",
    },
}


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "our",
    "say", "says", "should", "the", "their", "these", "this", "to", "what", "with",
    "about", "books", "book", "think", "tell", "explain",
}


def _normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace("_", "-")).strip()


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9'\-]{2,}", value.lower())
        if token not in STOPWORDS
    }


def _contains_term(query_norm: str, term: str) -> bool:
    term_norm = _normalise_text(term)
    if not term_norm:
        return False
    if " " in term_norm or "-" in term_norm:
        return term_norm in query_norm or term_norm.replace("-", " ") in query_norm
    return bool(re.search(rf"\b{re.escape(term_norm)}\b", query_norm))


def _add_score(scores: dict[str, float], key: str, amount: float) -> None:
    scores[key] = scores.get(key, 0.0) + amount


def _taxonomy_alias_scores(query: str) -> tuple[dict[str, float], dict[str, set[str]]]:
    taxonomy = load_taxonomy()
    query_norm = _normalise_text(query)
    query_tokens = _tokens(query)
    scores: dict[str, float] = {}
    matches: dict[str, set[str]] = {}

    # Score configured routing aliases directly.
    for alias, mapping in taxonomy.get("routing_aliases", {}).items():
        alias_text = alias.replace("_", " ")
        if _contains_term(query_norm, alias_text):
            _add_score(scores, alias, 4.0)
            matches.setdefault(alias, set()).add(alias_text)

        class_codes = list(mapping.get("primary_class", []) or []) + list(mapping.get("secondary_class", []) or [])
        for code in class_codes:
            cls = taxonomy.get("classes", {}).get(str(code), {})
            label = str(cls.get("label") or "")
            label_tokens = _tokens(label)
            overlap = query_tokens & label_tokens
            if overlap:
                _add_score(scores, alias, min(2.5, 0.6 * len(overlap)))
                matches.setdefault(alias, set()).update(overlap)
            for class_alias in cls.get("aliases", []) or []:
                alias_phrase = str(class_alias).replace("_", " ")
                if _contains_term(query_norm, alias_phrase):
                    _add_score(scores, alias, 2.5)
                    matches.setdefault(alias, set()).add(alias_phrase)

    return scores, matches


def route_query(query: str, max_aliases: int = 3) -> RouteResult:
    query_norm = _normalise_text(query)
    scores, matches = _taxonomy_alias_scores(query)
    reasons: list[str] = []

    for hint_name, hint in ROUTING_HINTS.items():
        hit_count = 0
        hit_terms: list[str] = []
        for term in hint.get("terms", []) or []:
            if _contains_term(query_norm, str(term)):
                hit_count += 1
                hit_terms.append(str(term))
        if hit_count:
            # Phrases and repeated domain hits should dominate incidental single-token matches.
            _add_score(scores, hint_name, 3.0 + (hit_count * 1.2))
            matches.setdefault(hint_name, set()).update(hit_terms[:8])
            reasons.append(str(hint.get("reason") or ""))

    if not scores:
        return RouteResult(
            query=query,
            aliases=[],
            class_codes=[],
            confidence=0.0,
            reason="No strong deterministic routing match was found, so BookMem should search summaries or the full corpus.",
            matched_terms=[],
        )

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    top_score = ranked[0][1]
    selected_base = [alias for alias, score in ranked if score >= max(2.5, top_score * 0.55)][:max_aliases]

    selected: list[str] = []
    seen_aliases: set[str] = set()
    for alias in selected_base:
        aliases_to_add = [alias]
        if alias in ROUTING_HINTS:
            aliases_to_add.extend(ROUTING_HINTS[alias].get("aliases", []) or [])
        for item in aliases_to_add:
            item = normalise_alias(str(item))
            if item and item not in seen_aliases:
                selected.append(item)
                seen_aliases.add(item)
            if len(selected) >= max_aliases:
                break
        if len(selected) >= max_aliases:
            break

    class_codes: list[str] = []
    seen_codes: set[str] = set()
    for alias in selected:
        # Prefer explicit hint classes; otherwise use only primary taxonomy classes.
        hint = ROUTING_HINTS.get(alias)
        if hint:
            candidate_codes = list(hint.get("class_codes", []) or [])
        else:
            resolved = resolve_alias(alias)
            candidate_codes = list(resolved.get("primary_class", []) or [])
        for code in candidate_codes:
            code = str(code)
            if code not in seen_codes:
                class_codes.append(code)
                seen_codes.add(code)

    matched_terms = sorted({term for alias in selected_base for term in matches.get(alias, set())})
    confidence = min(0.98, round(0.35 + (top_score / 12.0), 2))
    if len(selected) > 1:
        confidence = max(0.35, round(confidence - 0.05 * (len(selected) - 1), 2))

    if reasons:
        # Prefer the reason attached to the strongest selected hint.
        reason = next(
            (
                str(ROUTING_HINTS[alias]["reason"])
                for alias in selected
                if alias in ROUTING_HINTS and ROUTING_HINTS[alias].get("reason")
            ),
            reasons[0],
        )
    else:
        labels = [get_class_label(code) for code in class_codes[:3]]
        reason = "The query matched BookMem routing aliases and class labels: " + ", ".join(labels)

    return RouteResult(
        query=query,
        aliases=selected,
        class_codes=class_codes,
        confidence=confidence,
        reason=reason,
        matched_terms=matched_terms,
    )
