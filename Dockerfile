FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    PYTHONPATH=/app/backend

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY backend ./backend
COPY experiments/results/forecast_models.json ./experiments/results/forecast_models.json
COPY experiments/results/horizon_sensitivity.json ./experiments/results/horizon_sensitivity.json
COPY experiments/results/feature_ablation.json ./experiments/results/feature_ablation.json
COPY experiments/results/cvrp_benchmark.json ./experiments/results/cvrp_benchmark.json
COPY experiments/results/hgfc_advisory.json ./experiments/results/hgfc_advisory.json
COPY data/raw/synthetic_demand.csv ./data/raw/synthetic_demand.csv

RUN useradd -m -u 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]