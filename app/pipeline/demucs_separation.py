"""Musik-/Stimmtrennung mit Demucs.

Trennt eine Audiodatei in separate Spuren (vocals, drums, bass, other).
Für die Transkription wird primär die "vocals"-Spur benötigt, da sie
Hintergrundmusik entfernt und dadurch Whisper-Genauigkeit verbessert.
"""
import subprocess
import sys
from pathlib import Path


def separate_audio(input_path: Path, output_dir: Path) -> dict[str, Path]:
    """Führt Demucs auf der Eingabedatei aus und gibt Pfade zu den getrennten Spuren zurück.

    Nutzt das schnellere "htdemucs" Modell (Standard bei Demucs 4).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "demucs.separate",
        "-n",
        "htdemucs",
        "-o",
        str(output_dir),
        str(input_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # Demucs legt Ergebnisse unter {output_dir}/htdemucs/{stem_name}/*.wav ab
    stem_name = input_path.stem
    track_dir = output_dir / "htdemucs" / stem_name

    tracks = {}
    for stem in ["vocals", "drums", "bass", "other"]:
        stem_path = track_dir / f"{stem}.wav"
        if stem_path.exists():
            tracks[stem] = stem_path

    return tracks
