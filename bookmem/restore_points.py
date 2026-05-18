"""Restore points and rollback for BookMem.

The audit log records the timeline. Restore points provide the actual
recovery mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import shutil
import tarfile
tempfile
from typing import Any, Iterable

from .audit import append_audit_record, tail_audit, search_audit


RESTORE_POINTS_VERSION = "0.1.0"
RESTORE_POINTS_DIR = Path("data/restore-points")
RESTORE_INDEX_PATH = RESTORE_POINTS_DIR / "restore_points.json"

DEFAULT_SNAPSHOT_PATHS = [
    Path("data/manifests"),
    Path("data/summaries"),
    Path("data/concepts"),
    Path("data/graphs"),
    Path("data/notes"),
    Path("data/review"),
    Path("config"),
]

OPTIONAL_CANONICAL_PATHS = [
    Path("data/books"),
    Path("data/raw-books"),
]

REGENERABLE_EXCLUDES = [
    Path("data/lancedb"),
    Path(".venv"),
    Path("__pycache__"),
]


@dataclass
class RestorePoint:
    restore_point_id: str
    label: str
    created_at: str
    archive_path: str
    included_paths: list[str]
    include_canonical_books: bool
    reason: str | None = None
    audit_record: dict[str, Any] | None = None
    restore_points_version: str = RESTORE_POINTS_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "restore-point"


def restore_points_dir() -> Path:
    RESTORE_POINTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESTORE_POINTS_DIR


def load_restore_index() -> dict[str, Any]:
    path = RESTORE_INDEX_PATH
    if not path.exists():
        return {
            "schema_version": 1,
            "restore_points_version": RESTORE_POINTS_VERSION,
            "restore_points": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_restore_index(index: dict[str, Any]) -> None:
    restore_points_dir()
    index["restore_points_version"] = RESTORE_POINTS_VERSION
    RESTORE_INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalise_paths(paths: Iterable[str | Path] | None) -> list[Path]:
    if not paths:
        return []
    out: list[Path] = []
    seen = set()
    for item in paths:
        path = Path(item)
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_regenerable_excluded(path: Path) -> bool:
    resolved = path.resolve()
    for excluded in REGENERABLE_EXCLUDES:
        if path == excluded or is_within(path, excluded):
            return True
        try:
            if resolved == excluded.resolve() or str(resolved).startswith(str(excluded.resolve()) + "/"):
                return True
        except FileNotFoundError:
            continue
    return False


def collect_snapshot_paths(
    paths: Iterable[str | Path] | None = None,
    include_canonical_books: bool = False,
) -> list[Path]:
    selected = normalise_paths(paths) if paths else list(DEFAULT_SNAPSHOT_PATHS)
    if include_canonical_books:
        selected.extend(OPTIONAL_CANONICAL_PATHS)

    clean: list[Path] = []
    seen = set()
    for path in selected:
        if is_regenerable_excluded(path):
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            clean.append(path)
    return clean


def create_restore_point(
    label: str,
    paths: Iterable[str | Path] | None = None,
    include_canonical_books: bool = False,
    reason: str | None = None,
    audit_record: dict[str, Any] | None = None,
    write_audit: bool = True,
) -> RestorePoint:
    restore_points_dir()
    rp_id = f"{timestamp_id()}-{slugify(label)}"
    archive_path = RESTORE_POINTS_DIR / f"{rp_id}.tar.gz"
    included = collect_snapshot_paths(paths, include_canonical_books=include_canonical_books)

    manifest = {
        "restore_point_id": rp_id,
        "label": label,
        "created_at": utc_now_iso(),
        "reason": reason,
        "included_paths": [str(path) for path in included],
        "include_canonical_books": include_canonical_books,
        "audit_record": audit_record,
        "restore_points_version": RESTORE_POINTS_VERSION,
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "restore_point.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(manifest_path, arcname="restore_point.json")
            for path in included:
                if path.exists():
                    tar.add(path, arcname=str(path))

    rp = RestorePoint(
        restore_point_id=rp_id,
        label=label,
        created_at=manifest["created_at"],
        archive_path=str(archive_path),
        included_paths=[str(path) for path in included],
        include_canonical_books=include_canonical_books,
        reason=reason,
        audit_record=audit_record,
    )

    index = load_restore_index()
    points = index.get("restore_points", [])
    if not isinstance(points, list):
        points = []
    points.append(asdict(rp))
    index["restore_points"] = points
    save_restore_index(index)

    if write_audit:
        append_audit_record(
            action="restore_points.create",
            status="ok",
            changed_files=[archive_path, RESTORE_INDEX_PATH],
            target=rp_id,
            message=f"Created restore point: {label}",
            details={
                "restore_point_id": rp_id,
                "included_paths": rp.included_paths,
                "include_canonical_books": include_canonical_books,
                "reason": reason,
            },
        )

    return rp


def list_restore_points() -> list[dict[str, Any]]:
    index = load_restore_index()
    points = index.get("restore_points", [])
    if not isinstance(points, list):
        return []
    return sorted(points, key=lambda item: item.get("created_at") or "", reverse=True)


def get_restore_point(restore_point_id: str) -> dict[str, Any]:
    for item in list_restore_points():
        if item.get("restore_point_id") == restore_point_id:
            return item
    raise FileNotFoundError(f"Restore point not found: {restore_point_id}")


def last_restore_point() -> dict[str, Any]:
    points = list_restore_points()
    if not points:
        raise FileNotFoundError("No restore points found.")
    return points[0]


def archive_members(archive_path: Path) -> list[str]:
    with tarfile.open(archive_path, "r:gz") as tar:
        return tar.getnames()


def show_restore_point(restore_point_id: str) -> dict[str, Any]:
    point = get_restore_point(restore_point_id)
    archive_path = Path(point["archive_path"])
    members = archive_members(archive_path) if archive_path.exists() else []
    return {
        **point,
        "archive_exists": archive_path.exists(),
        "archive_members": members,
    }


def _safe_extract_tar(tar: tarfile.TarFile, destination: Path) -> None:
    dest = destination.resolve()
    for member in tar.getmembers():
        member_path = (destination / member.name).resolve()
        if not str(member_path).startswith(str(dest)):
            raise RuntimeError(f"Unsafe path in archive: {member.name}")
    tar.extractall(destination)


def rollback_restore_point(
    restore_point_id: str | None = None,
    *,
    last: bool = False,
    dry_run: bool = True,
    include_canonical_books: bool = False,
) -> dict[str, Any]:
    point = last_restore_point() if last else get_restore_point(str(restore_point_id))
    archive_path = Path(point["archive_path"])
    if not archive_path.exists():
        raise FileNotFoundError(f"Restore archive not found: {archive_path}")

    members = archive_members(archive_path)
    restore_members = [m for m in members if m != "restore_point.json"]

    protected = []
    for member in restore_members:
        path = Path(member)
        if (path == Path("data/books") or is_within(path, Path("data/books")) or
            path == Path("data/raw-books") or is_within(path, Path("data/raw-books"))):
            if not include_canonical_books:
                protected.append(member)

    if protected:
        return {
            "dry_run": dry_run,
            "restore_point_id": point["restore_point_id"],
            "archive_path": str(archive_path),
            "would_restore": restore_members,
            "blocked": protected,
            "status": "blocked",
            "message": "Restore point includes canonical books/raw books. Re-run with --include-canonical-books to restore them.",
        }

    if dry_run:
        return {
            "dry_run": True,
            "restore_point_id": point["restore_point_id"],
            "archive_path": str(archive_path),
            "would_restore": restore_members,
            "blocked": [],
            "status": "planned",
        }

    with tarfile.open(archive_path, "r:gz") as tar:
        _safe_extract_tar(tar, Path.cwd())

    append_audit_record(
        action="rollback.restore_point",
        status="ok",
        changed_files=restore_members,
        target=point["restore_point_id"],
        message=f"Rolled back to restore point {point['restore_point_id']}",
        details={
            "archive_path": str(archive_path),
            "include_canonical_books": include_canonical_books,
        },
    )

    return {
        "dry_run": False,
        "restore_point_id": point["restore_point_id"],
        "archive_path": str(archive_path),
        "restored": restore_members,
        "blocked": [],
        "status": "ok",
    }


def restore_point_from_audit_id(audit_query: str) -> dict[str, Any]:
    matches = search_audit(audit_query, limit=20)
    for record in reversed(matches):
        details = record.get("details") or {}
        rp_id = record.get("restore_point_id") or details.get("restore_point_id")
        rollback = record.get("rollback") or details.get("rollback") or {}
        if not rp_id and isinstance(rollback, dict):
            rp_id = rollback.get("restore_point_id")
        if rp_id:
            return get_restore_point(str(rp_id))
    raise FileNotFoundError(f"No restore point found in audit records matching: {audit_query}")


def restore_point_as_dict(point: RestorePoint) -> dict[str, Any]:
    return asdict(point)
