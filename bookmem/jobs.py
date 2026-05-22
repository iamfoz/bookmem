"""Job observability for long-running BookMem workflows."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import shlex
import sys
from typing import Any


JOBS_VERSION = "0.1.0"
JOBS_DIR = Path("data/jobs")

ACTIVE = "active"
OK = "ok"
WARN = "warn"
ERROR = "error"
CANCELLED = "cancelled"


@dataclass
class JobStatus:
    job_id: str
    started_at: str
    finished_at: str | None
    status: str
    command: str
    progress: float
    current_file: str | None
    files_processed: int
    errors: list[str]
    warnings: list[str]
    message: str | None = None
    jobs_version: str = JOBS_VERSION


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "job"


def current_command() -> str:
    return " ".join(shlex.quote(str(part)) for part in (sys.argv or ["bookmem"]))


def new_job_id(label: str | None = None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if label:
        return f"{stamp}-{slugify(label)}"
    return f"{stamp}-job"


def jobs_dir() -> Path:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    return JOBS_DIR


def job_json_path(job_id: str) -> Path:
    return jobs_dir() / f"{job_id}.json"


def job_log_path(job_id: str) -> Path:
    return jobs_dir() / f"{job_id}.log"


def write_job(status: JobStatus) -> None:
    job_json_path(status.job_id).write_text(json.dumps(asdict(status), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_job_log(job_id: str, message: str) -> None:
    path = job_log_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now_iso()} {message}\n")


def start_job(label: str | None = None, command: str | None = None, message: str | None = None) -> JobStatus:
    job_id = new_job_id(label)
    status = JobStatus(
        job_id=job_id,
        started_at=utc_now_iso(),
        finished_at=None,
        status=ACTIVE,
        command=command or current_command(),
        progress=0.0,
        current_file=None,
        files_processed=0,
        errors=[],
        warnings=[],
        message=message,
    )
    write_job(status)
    append_job_log(job_id, message or f"Started job {job_id}")
    return status


def read_job(job_id: str) -> JobStatus:
    path = job_json_path(job_id)
    if not path.exists():
        raise FileNotFoundError(f"Job not found: {job_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return JobStatus(**data)


def update_job(
    job_id: str,
    *,
    progress: float | None = None,
    current_file: str | None = None,
    files_processed: int | None = None,
    status: str | None = None,
    message: str | None = None,
    warning: str | None = None,
    error: str | None = None,
) -> JobStatus:
    job = read_job(job_id)
    if progress is not None:
        job.progress = max(0.0, min(1.0, float(progress)))
    if current_file is not None:
        job.current_file = current_file
    if files_processed is not None:
        job.files_processed = int(files_processed)
    if status is not None:
        job.status = status
    if message is not None:
        job.message = message
    if warning:
        job.warnings.append(warning)
    if error:
        job.errors.append(error)
        job.status = ERROR
    write_job(job)
    append_job_log(job_id, message or warning or error or "Job updated")
    return job


def finish_job(job_id: str, *, status: str = OK, message: str | None = None) -> JobStatus:
    job = read_job(job_id)
    job.status = status
    job.finished_at = utc_now_iso()
    if status == OK:
        job.progress = 1.0
    if message:
        job.message = message
    write_job(job)
    append_job_log(job_id, message or f"Finished job with status {status}")
    return job


def list_jobs(limit: int | None = None, status: str | None = None) -> list[dict[str, Any]]:
    rows = []
    if not jobs_dir().exists():
        return []
    for path in sorted(jobs_dir().glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if status and data.get("status") != status:
            continue
        data["json_path"] = str(path)
        data["log_path"] = str(path.with_suffix(".log"))
        rows.append(data)
    rows.sort(key=lambda row: row.get("started_at") or "", reverse=True)
    if limit:
        return rows[:limit]
    return rows


def tail_job(job_id: str, lines: int = 80) -> list[str]:
    path = job_log_path(job_id)
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return content[-lines:]


def job_as_dict(job: JobStatus) -> dict[str, Any]:
    return asdict(job)


class JobTracker:
    """Small context manager for instrumenting future long-running workflows."""

    def __init__(self, label: str | None = None, command: str | None = None):
        self.label = label
        self.command = command
        self.job: JobStatus | None = None

    def __enter__(self) -> "JobTracker":
        self.job = start_job(self.label, self.command)
        return self

    def update(self, **kwargs: Any) -> None:
        if self.job:
            self.job = update_job(self.job.job_id, **kwargs)

    def log(self, message: str) -> None:
        if self.job:
            append_job_log(self.job.job_id, message)

    def __exit__(self, exc_type, exc, tb) -> bool:
        if not self.job:
            return False
        if exc:
            update_job(self.job.job_id, error=str(exc), message=f"Failed: {exc}")
            finish_job(self.job.job_id, status=ERROR, message=f"Failed: {exc}")
            return False
        finish_job(self.job.job_id, status=OK, message="Job completed")
        return False
