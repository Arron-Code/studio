"""Orchestrierung der gesamten Pipeline: Trennung -> VAD -> Transkription -> Übersetzung."""
from pathlib import Path
from typing import Any

from app.job_store import JobStatus, update_job
from app.pipeline import demucs_separation, transcription, transcription_tigrinya, translation, vad


def run_pipeline(
    job_id: str,
    input_path: Path,
    work_dir: Path,
    *,
    separate_music: bool,
    target_languages: list[str],
    source_language: str | None = None,
) -> dict[str, Any]:
    """Führt die komplette Pipeline synchron aus (wird in einem Hintergrund-Thread aufgerufen).

    Schritte:
    1. (optional) Demucs: Musik/Stimme trennen, Vocals-Spur für die weitere Verarbeitung nutzen
    2. Silero VAD: Sprachabschnitte erkennen (informativ, im Ergebnis enthalten)
    3. Transkription: Whisper erkennt die Sprache automatisch UND transkribiert.
       Ausnahme: Tigrinya ("ti") wird von Whisper nicht unterstützt (fehlt in dessen
       Sprachliste) – ist source_language="ti" gesetzt, wird stattdessen das
       spezialisierte Ethio-ASR-Tigrinya-Modell verwendet (siehe transcription_tigrinya.py).
    4. NLLB-200: Übersetzung des Transkripts in die gewünschten Zielsprachen
    """
    update_job(job_id, status=JobStatus.PROCESSING, progress="Starte Verarbeitung")

    audio_for_transcription = input_path
    separated_tracks: dict[str, str] = {}

    if separate_music:
        update_job(job_id, progress="Trenne Musik und Stimme (Demucs)")
        tracks = demucs_separation.separate_audio(input_path, work_dir / "demucs")
        separated_tracks = {name: str(path) for name, path in tracks.items()}
        if "vocals" in tracks:
            audio_for_transcription = tracks["vocals"]

    update_job(job_id, progress="Erkenne Sprachabschnitte (Silero VAD)")
    speech_segments = vad.detect_speech_segments(audio_for_transcription)

    if source_language == "ti":
        update_job(job_id, progress="Transkribiere Tigrinya (Ethio-ASR)")
        transcript = transcription_tigrinya.transcribe(audio_for_transcription)
    else:
        update_job(job_id, progress="Transkribiere Sprache (Whisper)")
        transcript = transcription.transcribe(audio_for_transcription)
    source_lang = transcript["language"]

    translations: dict[str, Any] = {}
    for lang in target_languages:
        if lang == source_lang:
            continue
        update_job(job_id, progress=f"Übersetze nach '{lang}'")
        translations[lang] = {
            "text": translation.translate(transcript["text"], source_lang, lang),
            "segments": translation.translate_segments(
                transcript["segments"], source_lang, lang
            ),
        }

    result = {
        "source_language": source_lang,
        "speech_segments": speech_segments,
        "transcript": transcript,
        "translations": translations,
        "separated_tracks": separated_tracks,
    }

    update_job(job_id, status=JobStatus.DONE, progress="Fertig", result=result)
    return result
