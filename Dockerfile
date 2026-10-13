FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg + build deps for tgcrypto
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# keep yt-dlp up to date — site extractors change weekly
RUN pip install --upgrade yt-dlp

COPY . .

RUN mkdir -p downloads thumbnails

EXPOSE 8080

CMD ["python", "-u", "main.py"]
