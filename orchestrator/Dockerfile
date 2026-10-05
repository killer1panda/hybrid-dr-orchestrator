FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    make \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src/ /app/src/
COPY config.example.yaml /app/config.yaml

RUN useradd -u 1000 orchuser && chown -R orchuser:orchuser /app
USER orchuser

ENTRYPOINT ["python", "-m", "hybrid_dr.cli"]
CMD ["run"]
