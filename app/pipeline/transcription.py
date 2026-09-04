"""Spracherkennung (Transkription) mit faster-whisper."""
from pathlib import Path

from faster_whisper import WhisperModel

from app.config import DEVICE, WHISPER_MODEL_SIZE

_model: WhisperModel | None = None


def _load_model() -> WhisperModel:
    global _model
    if _model is None:
        compute_type = "int8" if DEVICE == "cpu" else "float16"
        _model = WhisperModel(WHISPER_MODEL_SIZE, device=DEVICE, compute_type=compute_type)
    return _model


def transcribe(audio_path: Path) -> dict:
    """Transkribiert eine Audiodatei und gibt Segmente mit Zeitstempeln zurück.

    Rückgabeformat:
    {
        "language": "de",
        "text": "Vollständiger Transkript-Text",
        "segments": [{"start": 0.0, "end": 3.2, "text": "..."}, ...]
    }
    """
    model = _load_model()
    segments_iter, info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)

    segments = []
    full_text_parts = []
    for segment in segments_iter:
        text = segment.text.strip()
        segments.append({"start": segment.start, "end": segment.end, "text": text})
        full_text_parts.append(text)

    return {
        "language": info.language,
        "text": " ".join(full_text_parts).strip(),
        "segments": segments,
    }
