# Medeber AI Pipeline – FastAPI-Service für Audio-KI-Verarbeitung.
# CPU-Image (kein CUDA). Für GPU-Betrieb siehe README.md.
FROM python:3.12-slim

# ffmpeg wird von torchaudio/soundfile/Demucs für das Dekodieren von Video-/Audiodateien benötigt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Speicherort für Uploads/Job-Ergebnisse – als Volume mounten, damit Daten
# einen Container-Neustart überleben (siehe docker-compose.yml).
RUN mkdir -p storage/uploads storage/jobs
VOLUME ["/app/storage"]

EXPOSE 8008

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
