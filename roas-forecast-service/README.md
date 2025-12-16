ROAS Forecast Service (D7 → D90)

Production-ready service for forecasting IAP / IAA ROAS at D90 using cohort-level metrics available at D0–D7.

Designed for UA optimization workflows with support for multi-level aggregation (micro / mid / macro) and strict leakage control.

Key Features

Targets: iap_roas_d90, iaa_roas_d90

Inference horizon: D7 → D90 (no target leakage)

Signals: cohort-level metrics only (privacy-safe)

Aggregation levels: micro / mid / macro

Stack: CatBoost, ClickHouse, FastAPI, Docker

Repository Structure
roas-forecast-service/
├── docker-compose.yml
├── Dockerfile.api
├── requirements.txt
├── sql/
│   └── schema.sql
├── src/
│   ├── api/
│   │   └── app.py
│   ├── core/
│   └── training/
│       └── train.py
├── scripts/
│   └── load_csv_to_clickhouse.py
└── README.md

Quick Start

The service is fully reproducible via Docker Compose.

1. Start services
cd roas-forecast-service
docker compose up -d --build
docker compose ps


Verify that both API and ClickHouse containers are running.

2. Apply database schema
docker cp ./sql/schema.sql roas-forecast-service-clickhouse-1:/tmp/schema.sql
docker exec -it roas-forecast-service-clickhouse-1 \
  clickhouse-client --multiquery < /tmp/schema.sql


Verify:

docker exec -it roas-forecast-service-clickhouse-1 \
  clickhouse-client --query "SHOW TABLES FROM roas"

3. Load cohort data

Example using HTTP insert (works well on Windows):

curl -sS \
  -H "Content-Type: text/plain" \
  --data-binary "@test_task_cl.csv" \
  "http://localhost:8123/?query=INSERT INTO roas.cohort_metrics FORMAT CSVWithNames"


Verify:

curl "http://localhost:8123/?query=SELECT count() FROM roas.cohort_metrics"

4. Train models

Training is executed inside the API container and saves model artifacts to /app/models.

docker exec -it roas-forecast-service-api-1 \
  python -m src.training.train


Verify artifacts:

docker exec -it roas-forecast-service-api-1 ls -lah /app/models


Expected files:

micro_iap_latest.cbm
micro_iaa_latest.cbm
mid_iap_latest.cbm
macro_iap_latest.cbm
...

5. Smoke test API

Health check:

curl http://localhost:8000/health


Prediction example (macro level):

curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "level": "macro",
    "target": "iap",
    "date_from": 250,
    "date_to": 260
  }'

Notes

Models are trained on historical cohorts and served via FastAPI.

Inference strictly uses D0–D7 features only (no leakage).

Aggregation level (micro / mid / macro) is selected per request.

ClickHouse is used as the single source of truth for cohort metrics.

Entry Points

API: src/api/app.py

Training: src/training/train.py

DB schema: sql/schema.sql

Docker: docker-compose.yml
