"""Sprachaktivitätserkennung (VAD) mit Silero VAD.

Erkennt Zeitabschnitte in einer Audiodatei, in denen tatsächlich gesprochen wird.
Das reduziert die Whisper-Verarbeitungszeit und verbessert die Genauigkeit,
da Stille/Musik-only-Abschnitte übersprungen werden können.
"""
from pathlib import Path

import torch


_model = None
_utils = None


def _load_model():
    global _model, _utils
    if _model is None:
        _model, _utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
    return _model, _utils


def detect_speech_segments(wav_path: Path, sample_rate: int = 16000) -> list[dict[str, float]]:
    """Gibt eine Liste von Sprachabschnitten als {"start": s, "end": s} (Sekunden) zurück."""
    model, utils = _load_model()
    get_speech_timestamps, _, read_audio, *_ = utils

    wav = read_audio(str(wav_path), sampling_rate=sample_rate)
    timestamps = get_speech_timestamps(
        wav, model, sampling_rate=sample_rate, return_seconds=True
    )
    return [{"start": ts["start"], "end": ts["end"]} for ts in timestamps]
