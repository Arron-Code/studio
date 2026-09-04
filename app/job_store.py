"""Einfacher dateibasierter Job-Store für asynchrone Verarbeitung.

Jeder Job wird als JSON-Datei unter storage/jobs/{job_id}.json abgelegt.
Das reicht für einen lokalen Single-Host-Service völlig aus und vermeidet
die Komplexität einer externen Queue (Redis/Celery) für diesen Anwendungsfall.
"""
import json
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from app.config import JOBS_DIR

_lock = threading.Lock()


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


def _job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def create_job(filename: str, options: dict[str, Any]) -> str:
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "filename": filename,
        "options": options,
        "status": JobStatus.QUEUED.value,
        "progress": "Warteschlange",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
        "error": None,
    }
    _write_job(job)
    return job_id


def update_job(
    job_id: str,
    *,
    status: Optional[JobStatus] = None,
    progress: Optional[str] = None,
    result: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    with _lock:
        job = _read_job(job_id)
        if job is None:
            return
        if status is not None:
            job["status"] = status.value
        if progress is not None:
            job["progress"] = progress
        if result is not None:
            job["result"] = result
        if error is not None:
            job["error"] = error
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        _write_job(job)


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    return _read_job(job_id)


def _read_job(job_id: str) -> Optional[dict[str, Any]]:
    path = _job_path(job_id)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_job(job: dict[str, Any]) -> None:
    path = _job_path(job["job_id"])
    with path.open("w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, indent=2)
