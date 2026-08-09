# One image for all departments — built once, reused for containers that
# differ only in the $DEPARTMENT env var. On a 13 GB disk budget, building a
# near-identical image per department (each paying its own ~250MB
# Python-slim + deps layer) was the single biggest waste in the old
# 22-service layout; this build happens once and every department shares
# the same layers.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY shared /shared
RUN pip install /shared

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY microservices/ ./microservices/
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8000
# DEPARTMENT selects which of microservices/<department> to run — set per
# service in docker-compose.yml (identity, engagement, content, backoffice,
# academics, calendar).
CMD ["./entrypoint.sh"]
