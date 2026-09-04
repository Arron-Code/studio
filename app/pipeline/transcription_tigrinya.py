"""Tigrinya-Spracherkennung mit einem spezialisierten ASR-Modell.

Whisper (faster-whisper) unterstützt Tigrinya NICHT – es fehlt in der Liste
der ca. 99 von Whisper erkannten Sprachen. Bei Tigrinya-Audio rät Whisper
stattdessen eine ähnliche Sprache (z.B. Amharic/Arabisch), was zu falscher
Transkription und in der Folge zu Übersetzungsfehlern führt.

Für Tigrinya wird daher stattdessen "badrex/Ethio-ASR-tigrinya" verwendet,
ein auf wav2vec2-bert-2.0 basierendes Modell, das speziell auf Tigrinya
(WAXAL Speech Dataset) trainiert wurde (WER ca. 35 %).
Modellkarte: https://huggingface.co/badrex/Ethio-ASR-tigrinya
"""
from pathlib import Path

import torch
import torchaudio
from transformers import AutoModelForCTC, AutoProcessor

from app.config import DEVICE

MODEL_NAME = "badrex/Ethio-ASR-tigrinya"
TARGET_SAMPLE_RATE = 16000

_model = None
_processor = None


def _load_model():
    global _model, _processor
    if _model is None:
        _processor = AutoProcessor.from_pretrained(MODEL_NAME)
        _model = AutoModelForCTC.from_pretrained(MODEL_NAME).to(DEVICE)
        _model.eval()
    return _model, _processor


def transcribe(audio_path: Path) -> dict:
    """Transkribiert eine Tigrinya-Audiodatei.

    Das Modell liefert (im Gegensatz zu Whisper) keine Zeitstempel pro
    Segment, daher enthält "segments" hier nur ein einzelnes Segment über
    die gesamte Audiolänge. Rückgabeformat kompatibel zu transcription.transcribe():
    {
        "language": "ti",
        "text": "Vollständiger Transkript-Text",
        "segments": [{"start": 0.0, "end": <dauer>, "text": "..."}]
    }
    """
    model, processor = _load_model()

    waveform, sample_rate = torchaudio.load(str(audio_path))
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    if sample_rate != TARGET_SAMPLE_RATE:
        waveform = torchaudio.functional.resample(waveform, sample_rate, TARGET_SAMPLE_RATE)

    duration = waveform.shape[1] / TARGET_SAMPLE_RATE

    inputs = processor(
        waveform.squeeze(0), sampling_rate=TARGET_SAMPLE_RATE, return_tensors="pt"
    ).to(DEVICE)

    with torch.no_grad():
        logits = model(**inputs).logits

    predicted_ids = torch.argmax(logits, dim=-1)
    text = processor.batch_decode(predicted_ids)[0].strip()

    return {
        "language": "ti",
        "text": text,
        "segments": [{"start": 0.0, "end": duration, "text": text}],
    }
