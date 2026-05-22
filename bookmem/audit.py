"""Durable JSONL audit log for BookMem.

The audit log is intended for agent infrastructure: it records actions,
changed files, providers and status in a machine-readable trail.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import shlex
import sys
from typing import Any, Iterable


AUDIT_VERSION = "0.1.0"
AUDIT_LOG_PATH = Path("data/audit/bookmem.log.jsonl")


@dataclass
class AuditRecord:
    timestamp: str
    command: str
    action: str
    status: str
    changed_files: list[str]
    provider: str | None = None
    target: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None
    audit_version: str = AUDIT_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def current_command() -> str:
    argv = sys.argv or ["bookmem"]
    return " ".join(shlex.quote(str(part)) for part in argv)


def audit_log_path() -> Path:
    return AUDIT_LOG_PATH


def normalise_files(paths: Iterable[str | Path] | None) -> list[str]:
    if not paths:
        return []
    out = []
    for path in paths:
        text = str(path)
        if text not in out:
            out.append(text)
    return out


def append_audit_record(
    *,
    action: str,
    status: str = "ok",
    changed_files: Iterable[str | Path] | None = None,
    provider: str | None = None,
    target: str | None = None,
    message: str | None = None,
    details: dict[str, Any] | None = None,
    command: str | None = None,
) -> AuditRecord:
    record = AuditRecord(
        timestamp=utc_now_iso(),
        command=command or current_command(),
        action=action,
        status=status,
        changed_files=normalise_files(changed_files),
        provider=provider,
        target=target,
        message=message,
        details=details or {},
    )
    path = audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    return record


def read_audit_records(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or audit_log_path()
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                item = {
                    "timestamp": None,
                    "command": None,
                    "action": "parse_error",
                    "status": "error",
                    "changed_files": [],
                    "message": line,
                }
            records.append(item)
    return records


def tail_audit(limit: int = 50, path: Path | None = None) -> list[dict[str, Any]]:
    records = read_audit_records(path)
    return records[-limit:]


def search_audit(query: str, limit: int = 100, path: Path | None = None) -> list[dict[str, Any]]:
    q = query.lower()
    matches = []
    for record in read_audit_records(path):
        haystack = json.dumps(record, ensure_ascii=False).lower()
        if q in haystack:
            matches.append(record)
    return matches[-limit:]


def export_audit(format: str = "jsonl", path: Path | None = None) -> str:
    records = read_audit_records(path)
    fmt = format.lower()
    if fmt == "jsonl":
        return "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + ("\n" if records else "")
    if fmt == "json":
        return json.dumps(records, indent=2, ensure_ascii=False) + "\n"
    raise ValueError(f"Unsupported audit export format: {format}")


def audit_record_as_dict(record: AuditRecord) -> dict[str, Any]:
    return asdict(record)
