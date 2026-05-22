"""Safe generated artefact cleaner for BookMem.

This module only cleans derived/generated state. It must never delete
canonical books, raw books or config.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import shutil
from typing import Any



CLEAN_DERIVED_VERSION = "0.1.0"

PROTECTED_PATHS = {
    Path("data/books"),
    Path("data/raw-books"),
    Path("config"),
}

DEFAULT_TARGETS = {
    "summaries": [Path("data/summaries")],
    "concepts": [Path("data/concepts")],
    "graphs": [Path("data/graphs")],
    "index": [Path("data/lancedb")],
    "notes": [Path("data/notes")],
    "exports": [Path("exports")],
}

REVIEW_TARGETS = {
    "review": [Path("data/review")],
}


@dataclass
class CleanCandidate:
    target: str
    path: str
    exists: bool
    protected: bool
    type: str
    size_bytes: int


@dataclass
class CleanResult:
    dry_run: bool
    deleted: list[str]
    skipped: list[str]
    candidates: list[CleanCandidate]
    warnings: list[str]


def is_protected(path: Path) -> bool:
    resolved = path.resolve()
    for protected in PROTECTED_PATHS:
        p = protected.resolve()
        if resolved == p or str(resolved).startswith(str(p) + "/"):
            return True
    return False


def path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def path_type(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.is_file():
        return "file"
    if path.is_dir():
        return "directory"
    return "other"


def selected_targets(
    *,
    summaries: bool = False,
    concepts: bool = False,
    graphs: bool = False,
    index: bool = False,
    notes: bool = False,
    exports: bool = False,
    review: bool = False,
    all_targets: bool = False,
) -> dict[str, list[Path]]:
    targets: dict[str, list[Path]] = {}

    if all_targets:
        for key, paths in DEFAULT_TARGETS.items():
            targets[key] = list(paths)

    explicit = {
        "summaries": summaries,
        "concepts": concepts,
        "graphs": graphs,
        "index": index,
        "notes": notes,
        "exports": exports,
    }

    for key, enabled in explicit.items():
        if enabled:
            targets[key] = list(DEFAULT_TARGETS[key])

    if review:
        targets["review"] = list(REVIEW_TARGETS["review"])

    return targets


def build_candidates(targets: dict[str, list[Path]]) -> list[CleanCandidate]:
    candidates = []
    for target, paths in targets.items():
        for path in paths:
            candidates.append(
                CleanCandidate(
                    target=target,
                    path=str(path),
                    exists=path.exists(),
                    protected=is_protected(path),
                    type=path_type(path),
                    size_bytes=path_size(path),
                )
            )
    return candidates


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def recreate_gitkeep_for_allowed_dirs(path: Path) -> None:
    """Recreate empty derived directory with .gitkeep when useful."""
    derived_dirs = {
        Path("data/summaries"),
        Path("data/concepts"),
        Path("data/graphs"),
        Path("data/notes"),
        Path("data/review"),
    }
    if path in derived_dirs:
        path.mkdir(parents=True, exist_ok=True)
        (path / ".gitkeep").write_text("", encoding="utf-8")


def clean_derived(
    *,
    summaries: bool = False,
    concepts: bool = False,
    graphs: bool = False,
    index: bool = False,
    notes: bool = False,
    exports: bool = False,
    review: bool = False,
    all_targets: bool = False,
    dry_run: bool = True,
) -> CleanResult:
    targets = selected_targets(
        summaries=summaries,
        concepts=concepts,
        graphs=graphs,
        index=index,
        notes=notes,
        exports=exports,
        review=review,
        all_targets=all_targets,
    )

    warnings: list[str] = []
    if not targets:
        warnings.append("No derived targets selected. Use --summaries, --concepts, --graphs, --index, --notes, --exports, --review or --all.")

    if all_targets and not review:
        warnings.append("--all does not include review queues. Add --review explicitly to clean data/review.")

    candidates = build_candidates(targets)
    deleted: list[str] = []
    skipped: list[str] = []

    for candidate in candidates:
        path = Path(candidate.path)

        if candidate.protected:
            skipped.append(candidate.path)
            warnings.append(f"Protected path skipped: {candidate.path}")
            continue

        if not candidate.exists:
            skipped.append(candidate.path)
            continue

        if dry_run:
            skipped.append(candidate.path)
            continue

        remove_path(path)
        deleted.append(candidate.path)
        recreate_gitkeep_for_allowed_dirs(path)

    return CleanResult(
        dry_run=dry_run,
        deleted=deleted,
        skipped=skipped,
        candidates=candidates,
        warnings=warnings,
    )


def clean_result_as_dict(result: CleanResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["clean_derived_version"] = CLEAN_DERIVED_VERSION
    return payload
