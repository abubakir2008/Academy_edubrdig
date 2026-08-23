# Own image, separate from the shared department image (platform/Dockerfile)
# -- this needs ffmpeg and the LiveKit realtime SDK, neither of which any
# FastAPI department uses, so bundling it into their shared image would
# grow every department's footprint for a dependency only this one needs.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# fonts-dejavu-core: full Cyrillic (and Latin) coverage for the "camera off"
# placeholder tiles composite_recorder.py draws (participant names here are
# routinely Cyrillic) -- Pillow's own built-in default font can't be relied
# on to cover that.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY watcher.py recorder_bot.py composite_recorder.py ./

CMD ["python", "watcher.py"]
