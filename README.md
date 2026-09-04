# Medeber AI Pipeline

Eigenständiger, lokal laufender KI-Service für Audio-/Video-Verarbeitung:
Spracherkennung, Sprachaktivitätserkennung, Musik-/Stimmtrennung und
Übersetzung – vollständig offline nach dem initialen Modell-Download.

Dieses Projekt ist **losgelöst von Medeber**, kann aber von Medeber (oder
jeder anderen lokalen Anwendung) über eine einfache HTTP-API genutzt werden.

## Pipeline-Schritte

1. **Demucs** *(optional)* – trennt Musik/Instrumental von der Gesangs-/Sprachspur,
   damit die Transkription auch bei Hintergrundmusik (z. B. Vlogs, Musikvideos) sauber funktioniert.
2. **Silero VAD** – erkennt Zeitabschnitte, in denen tatsächlich gesprochen wird.
3. **Whisper** (via `faster-whisper`) – transkribiert die Sprache mit Zeitstempeln,
   erkennt automatisch die Ausgangssprache.
4. **NLLB-200** – lokales, mehrsprachiges Übersetzungsmodell; übersetzt das Transkript
   in beliebige Zielsprachen aus `{de, en, ti}` (Deutsch, Englisch, Tigrinya).

## Setup

Voraussetzungen: **Python 3.12**, **ffmpeg** (im PATH).

```powershell
cd medeber-ai-pipeline
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Hinweis GPU:** Die `requirements.txt` installiert CPU-Wheels von PyTorch.
> Für eine NVIDIA-GPU installiere stattdessen vorab die passende CUDA-Version
> gemäß [pytorch.org/get-started](https://pytorch.org/get-started/locally/), z. B.:
> ```powershell
> pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
> ```
> und setze `DEVICE = "cuda"` in `app/config.py`.

### Server starten

```powershell
uvicorn app.main:app --reload --port 8008
```

> Um Werte aus einer `.env`-Datei zu laden (z. B. `AI_PIPELINE_API_KEY`), nutze
> `uvicorn app.main:app --port 8008 --env-file .env` (uvicorn liest die Datei
> nativ ein, es ist kein zusätzliches Paket nötig).

Die interaktive API-Doku ist danach unter `http://localhost:8008/docs` erreichbar.

> Der **erste** Aufruf jedes Pipeline-Schritts lädt das jeweilige Modell aus dem
> Internet herunter (Whisper, Silero VAD, Demucs, NLLB-200 – insgesamt mehrere GB).
> Danach läuft alles vollständig offline aus dem lokalen Modell-Cache.

## API

### `POST /process`

Multipart-Form-Upload:

| Feld               | Typ      | Beschreibung                                              |
|--------------------|----------|------------------------------------------------------------|
| `file`             | Datei    | Audio-/Videodatei (`.mp3`, `.wav`, `.m4a`, `.mp4`, `.mov`, …) |
| `separate_music`   | bool     | `true`, um Demucs vorzuschalten (Standard: `false`)         |
| `target_languages` | string   | kommagetrennt, z. B. `"en,ti"`                              |

Antwort: `{ "job_id": "...", "status": "queued", "progress": "Warteschlange" }`

### `GET /jobs/{job_id}`

Gibt den aktuellen Status zurück:

```json
{
  "job_id": "...",
  "status": "done",
  "progress": "Fertig",
  "result": {
    "source_language": "de",
    "speech_segments": [{"start": 0.5, "end": 4.2}],
    "transcript": {
      "language": "de",
      "text": "...",
      "segments": [{"start": 0.5, "end": 4.2, "text": "..."}]
    },
    "translations": {
      "en": { "text": "...", "segments": [...] },
      "ti": { "text": "...", "segments": [...] }
    },
    "separated_tracks": { "vocals": "...", "drums": "...", "bass": "...", "other": "..." }
  }
}
```

`status` ist eines von: `queued`, `processing`, `done`, `error`.

## Beispiel-Aufruf (curl)

```bash
curl -X POST http://localhost:8008/process \
  -F "file=@kursvideo.mp4" \
  -F "separate_music=false" \
  -F "target_languages=en,ti"

curl http://localhost:8008/jobs/<job_id>
```

## Nutzung durch Medeber

Medeber ruft diesen Service über einen einfachen fetch-Client auf
(siehe `medeber/src/lib/ai-pipeline.ts`), z. B. um bei Kursvideo-Uploads
automatisch Untertitel/Transkripte in Deutsch, Englisch und Tigrinya zu erzeugen.
Der Service muss dafür lokal laufen (`uvicorn app.main:app --port 8008`).

## Projektstruktur

```
app/
  main.py                     # FastAPI-Endpunkte
  config.py                   # Zentrale Konfiguration (Modellgrößen, Pfade, Sprachen)
  job_store.py                # Dateibasierter Job-Status-Speicher
  pipeline/
    vad.py                    # Silero VAD – Sprachabschnitte erkennen
    demucs_separation.py      # Demucs – Musik-/Stimmtrennung
    transcription.py          # faster-whisper – Spracherkennung
    translation.py            # NLLB-200 – Übersetzung
    orchestrator.py           # Verkettet alle Schritte zu einer Pipeline
storage/
  uploads/{job_id}/           # Hochgeladene Originaldateien
  jobs/{job_id}.json          # Job-Status & Ergebnis
  jobs/{job_id}/demucs/       # Zwischenergebnisse der Musiktrennung
```

## Sicherer Betrieb auf einer eigenen VM (für Vercel-Anbindung)

Da Whisper, Demucs und NLLB-200 zu groß/rechenintensiv für Vercel-Functions sind
(keine GPU, kein `ffmpeg`, harte Zeit-/Größenlimits), läuft dieser Service auf
einer eigenen Maschine (VM, Homeserver, Cloud-VM) und wird von der auf Vercel
gehosteten Medeber-App per HTTPS-API angesprochen.

### 1. API-Key setzen (Pflicht, sobald der Service aus dem Internet erreichbar ist)

```powershell
# .env im medeber-ai-pipeline Verzeichnis (oder Umgebungsvariable der VM)
AI_PIPELINE_API_KEY=ein-langer-zufaelliger-schluessel
AI_PIPELINE_CORS_ORIGINS=https://medeber.vercel.app
```

Ohne `AI_PIPELINE_API_KEY` bleibt der Service ungeschützt – nur für rein
lokale Nutzung ohne Port-Weiterleitung ins Internet akzeptabel.

### 2. Service dauerhaft laufen lassen (systemd, Linux-VM)

```ini
# /etc/systemd/system/medeber-ai-pipeline.service
[Unit]
Description=Medeber AI Pipeline
After=network.target

[Service]
WorkingDirectory=/opt/medeber-ai-pipeline
Environment="AI_PIPELINE_API_KEY=ein-langer-zufaelliger-schluessel"
Environment="AI_PIPELINE_CORS_ORIGINS=https://medeber.vercel.app"
ExecStart=/opt/medeber-ai-pipeline/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8008
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now medeber-ai-pipeline
```

### 3. Von außen erreichbar machen

Am einfachsten über einen Reverse-Proxy mit TLS (z.B. Caddy oder nginx +
Let's Encrypt), damit der Endpunkt per `https://ki.meine-domain.de` statt
unverschlüsseltem HTTP erreichbar ist:

```
# Caddyfile
ki.meine-domain.de {
    reverse_proxy localhost:8008
}
```

### 4. Vercel (Medeber) mit der VM verbinden

In den Vercel-Projekteinstellungen (Settings → Environment Variables) für
das Medeber-Projekt setzen:

| Variable              | Wert                                  |
|-----------------------|----------------------------------------|
| `AI_PIPELINE_URL`     | `https://ki.meine-domain.de`           |
| `AI_PIPELINE_API_KEY` | derselbe Wert wie `AI_PIPELINE_API_KEY` auf der VM |

Danach in Vercel neu deployen (Redeploy). Medeber ruft die KI-Pipeline dann
über diese URL mit dem `X-API-Key`-Header auf – die schwere Verarbeitung
läuft weiterhin vollständig auf der eigenen VM, nicht auf Vercel.

## Hinweis: Dieses Projekt selbst NICHT auf Vercel deployen

Dieses Repository (`medeber-ai-pipeline` / `studio`) ist ein reiner
Python/FastAPI-Dauerdienst mit GB-großen ML-Modellen und `ffmpeg`-Abhängigkeit.
Vercel-Functions sind dafür ungeeignet (kein unterstütztes Framework, keine
GPU, harte Zeit-/Größenlimits, kein persistenter Prozess). Nur die
schlanke Next.js-App **Medeber** wird auf Vercel gehostet; dieser Service
läuft auf der eigenen VM.

## Hardware-Anforderungen

- **CPU-only:** funktioniert, ist aber bei größeren Dateien/Modellen (z. B. Whisper "medium"/"large")
  spürbar langsam. Für den Alltagsgebrauch empfiehlt sich Whisper-Modellgröße `small` oder `base`
  (einstellbar in `app/config.py`).
- **GPU (NVIDIA/CUDA):** deutlich schnellere Verarbeitung, empfohlen für Produktivbetrieb
  mit längeren Kursvideos.
- **Speicherplatz:** Modell-Downloads (Whisper, Demucs, NLLB-200, Silero VAD) benötigen
  insgesamt ca. 3–5 GB freien Speicherplatz beim ersten Start.
