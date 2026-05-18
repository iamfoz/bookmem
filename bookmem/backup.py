"""Backup and restore support for BookMem."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import tarfile
from typing import Any


BACKUP_SCHEMA_VERSION = 1
BACKUP_TOOL_VERSION = "0.1.0"

DEFAULT_INCLUDE_PATHS = [
    Path("data/books"),
    Path("data/summaries"),
    Path("data/notes"),
    Path("data/manifests"),
    Path("data/review"),
    Path("config"),
    Path("CHANGELOG.md"),
    Path("README.md"),
    Path("pyproject.toml"),
    Path("LICENSE"),
    Path("AUTHORS.md"),
    Path("NOTICE"),
]

DEFAULT_EXCLUDE_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "data/lancedb",
    "exports",
    "backups",
}


@dataclass
class BackupResult:
    output_path: str
    file_count: int
    included_paths: list[str]
    excluded_paths: list[str]
    manifest: dict[str, Any]


@dataclass
class RestoreResult:
    archive_path: str
    restored_count: int
    restored_paths: list[str]
    skipped_paths: list[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalise_rel_path(path: Path) -> str:
    return path.as_posix().lstrip("./")


def should_exclude(path: Path) -> bool:
    rel = normalise_rel_path(path)
    parts = set(path.parts)
    if parts & DEFAULT_EXCLUDE_PARTS:
        return True
    for excluded in DEFAULT_EXCLUDE_PARTS:
        if rel == excluded or rel.startswith(excluded.rstrip("/") + "/"):
            return True
    return False


def iter_backup_files(root: Path, include_paths: list[Path] | None = None):
    include_paths = include_paths or DEFAULT_INCLUDE_PATHS
    for include in include_paths:
        candidate = root / include
        if not candidate.exists():
            continue

        if candidate.is_file():
            if not should_exclude(include):
                yield candidate, include
            continue

        for path in sorted(candidate.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if should_exclude(rel):
                continue
            yield path, rel


def create_backup(
    output_path: Path,
    root: Path | None = None,
    include_paths: list[Path] | None = None,
    overwrite: bool = False,
) -> BackupResult:
    root = root or Path.cwd()
    output_path = output_path.expanduser()

    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Backup already exists: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = list(iter_backup_files(root, include_paths=include_paths))
    manifest = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "tool_version": BACKUP_TOOL_VERSION,
        "created_at": utc_now_iso(),
        "root": str(root),
        "file_count": len(files),
        "included": [normalise_rel_path(rel) for _path, rel in files],
        "excluded_policy": sorted(DEFAULT_EXCLUDE_PARTS),
        "note": "BookMem backup excludes rebuildable/generated-heavy state such as data/lancedb and exports.",
    }

    with tarfile.open(output_path, "w:gz") as tar:
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        import io

        info = tarfile.TarInfo("bookmem-backup-manifest.json")
        info.size = len(manifest_bytes)
        info.mtime = int(datetime.now(timezone.utc).timestamp())
        tar.addfile(info, io.BytesIO(manifest_bytes))

        for path, rel in files:
            tar.add(path, arcname=normalise_rel_path(rel), recursive=False)

    return BackupResult(
        output_path=str(output_path),
        file_count=len(files),
        included_paths=[normalise_rel_path(rel) for _path, rel in files],
        excluded_paths=sorted(DEFAULT_EXCLUDE_PARTS),
        manifest=manifest,
    )


def safe_extract_path(target_root: Path, member_name: str) -> Path:
    target = (target_root / member_name).resolve()
    root = target_root.resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"Unsafe path in backup archive: {member_name}")
    return target


def inspect_backup(archive_path: Path) -> dict[str, Any]:
    with tarfile.open(archive_path, "r:gz") as tar:
        try:
            member = tar.getmember("bookmem-backup-manifest.json")
            fh = tar.extractfile(member)
            if fh is None:
                return {}
            return json.loads(fh.read().decode("utf-8"))
        except KeyError:
            return {}


def restore_backup(
    archive_path: Path,
    target_root: Path | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> RestoreResult:
    target_root = target_root or Path.cwd()
    archive_path = archive_path.expanduser()

    restored: list[str] = []
    skipped: list[str] = []

    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isdir():
                continue
            if member.name == "bookmem-backup-manifest.json":
                continue

            target = safe_extract_path(target_root, member.name)
            rel = normalise_rel_path(Path(member.name))

            if target.exists() and not overwrite:
                skipped.append(rel)
                continue

            if dry_run:
                restored.append(rel)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = tar.extractfile(member)
            if extracted is None:
                skipped.append(rel)
                continue
            target.write_bytes(extracted.read())
            restored.append(rel)

    return RestoreResult(
        archive_path=str(archive_path),
        restored_count=len(restored),
        restored_paths=restored,
        skipped_paths=skipped,
    )


def result_as_dict(result: BackupResult | RestoreResult) -> dict[str, Any]:
    return asdict(result)
