"""Zentrale Konfiguration der Medeber AI Pipeline."""
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
