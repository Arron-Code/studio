"""Medeber AI Pipeline – FastAPI-Service für Audio-KI-Verarbeitung.
Läuft auf einer eigenen VM/Maschine (nicht auf Vercel) und wird von der
Next.js-App Medeber per HTTPS-API angesprochen (siehe README).

Endpunkte:
  POST /process        Datei hochladen, Verarbeitung als Hintergrund-Job starten
  GET  /jobs/{job_id}   Status und (sobald fertig) Ergebnis eines Jobs abfragen
  GET  /health          Health-Check
"""
import shutil
import threading
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import (
    ALLOWED_EXTENSIONS,
    API_KEY,
    CORS_ORIGINS,
    JOBS_DIR,
    MAX_UPLOAD_SIZE_BYTES,
    UPLOADS_DIR,
)
from app.job_store import JobStatus, create_job, get_job, update_job
from app.pipeline.orchestrator import run_pipeline

app = FastAPI(
    title="Medeber AI Pipeline",
    description=(
        "Eigenständiger KI-Service: Spracherkennung (Whisper), "
        "Sprachaktivitätserkennung (Silero VAD), Musik-/Stimmtrennung (Demucs) "
        "und lokale Übersetzung (NLLB-200) für Deutsch, Englisch und Tigrinya. "
        "Läuft auf einer eigenen VM/Maschine und wird per API (optional mit "
        "API-Key) von Medeber (z.B. gehostet auf Vercel) angesprochen."
    ),
    version="0.1.0",
)

# Erlaubt Zugriff von Medeber per Browser-/Server-Fetch. In Produktion sollte
# AI_PIPELINE_CORS_ORIGINS auf die konkrete(n) Medeber-Domain(s) eingeschränkt werden.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Prüft den API-Key, falls einer konfiguriert ist (AI_PIPELINE_API_KEY).

    Ist kein Key konfiguriert, bleibt der Service offen (nur für rein lokale
    Nutzung ohne Internet-Exposition akzeptabel).
    """
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Ungültiger oder fehlender API-Key.")


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process", response_model=JobResponse, dependencies=[Depends(require_api_key)])
async def process_audio(
    file: UploadFile = File(...),
    separate_music: bool = Form(False),
    target_languages: str = Form("en"),
) -> JobResponse:
    """Nimmt eine Audio-/Videodatei entgegen und startet die Verarbeitungs-Pipeline.

    - separate_music: falls True, wird Demucs zur Vocals-Extraktion vorgeschaltet
    - target_languages: kommagetrennte Liste von Zielsprachen, z.B. "en,ti"
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Dateityp '{suffix}' nicht unterstützt. Erlaubt: {sorted(ALLOWED_EXTENSIONS)}",
        )

    languages = [lang.strip() for lang in target_languages.split(",") if lang.strip()]

    job_id = create_job(file.filename or "upload", {"separate_music": separate_music, "target_languages": languages})

    job_upload_dir = UPLOADS_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = job_upload_dir / f"input{suffix}"

    size = 0
    with input_path.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_SIZE_BYTES:
                shutil.rmtree(job_upload_dir, ignore_errors=True)
                raise HTTPException(status_code=413, detail="Datei zu groß (max. 500 MB)")
            f.write(chunk)

    work_dir = JOBS_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    def _run() -> None:
        try:
            run_pipeline(
                job_id,
                input_path,
                work_dir,
                separate_music=separate_music,
                target_languages=languages,
            )
        except Exception as exc:  # noqa: BLE001 - Fehler soll im Job-Status sichtbar sein
            update_job(job_id, status=JobStatus.ERROR, progress="Fehler", error=str(exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return JobResponse(job_id=job_id, status=JobStatus.QUEUED.value, progress="Warteschlange")


@app.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_job_status(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job
