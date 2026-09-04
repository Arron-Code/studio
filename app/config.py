"""Zentrale Konfiguration der Medeber AI Pipeline."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
JOBS_DIR = STORAGE_DIR / "jobs"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Whisper-Modellgröße: tiny/base/small/medium/large-v3 (größer = genauer, aber langsamer)
WHISPER_MODEL_SIZE = "small"

# Gerät für Torch-Modelle: "cpu" oder "cuda" (wird beim Start automatisch erkannt)
DEVICE = "cpu"

# Von der Pipeline unterstützte Sprachen für die Übersetzung (NLLB-200 Sprachcodes)
NLLB_LANG_CODES = {
    "de": "deu_Latn",
    "en": "eng_Latn",
    "ti": "tir_Ethi",
}

TRANSLATION_MODEL_NAME = "facebook/nllb-200-distilled-600M"

MAX_UPLOAD_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".mov", ".webm", ".ogg", ".flac"}

# API-Key-Absicherung: Wird die VM per Internet erreichbar gemacht (z.B. damit Vercel
# darauf zugreifen kann), MUSS dieser Wert per Umgebungsvariable gesetzt werden.
# Ist er leer, läuft der Service ungeschützt (nur für rein lokale Nutzung akzeptabel).
API_KEY = os.environ.get("AI_PIPELINE_API_KEY", "").strip()

# Kommagetrennte Liste erlaubter Origins für CORS, z.B. "https://medeber.vercel.app".
# Leer/"*" erlaubt alle Origins (Standard für lokale Entwicklung).
_cors_env = os.environ.get("AI_PIPELINE_CORS_ORIGINS", "*").strip()
CORS_ORIGINS = ["*"] if _cors_env in ("", "*") else [o.strip() for o in _cors_env.split(",") if o.strip()]
