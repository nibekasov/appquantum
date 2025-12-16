# ROAS Forecast Service (D7 → D90)

Production-ready service for forecasting **IAP / IAA ROAS at D90** using cohort metrics available at **D0–D7**.  
Designed for **UA optimization workflows** and **multi-level aggregation** (micro / mid / macro).

---

## Key Features

- **Targets:** `iap_roas_d90`, `iaa_roas_d90`
- **Inference horizon:** D7 → D90 (no leakage)
- **Signals:** cohort-level metrics only (privacy-safe)
- **Levels:** micro / mid / macro
- **Stack:** CatBoost, ClickHouse, FastAPI, Docker

---

## Repository Structure
```text
roas-forecast-service/
  ├── docker-compose.yml
  ├── requirements.txt
  ├── sql/
  │ └── schema.sql
  ├── src/
  │ ├── api/
  │ │ └── app.py
  │ ├── core/
  │ └── training/
  │ └── train.py
  ├── scripts/
  │ └── load_csv_to_clickhouse.py
  └── README.md
```



---

## Quick Start (Windows-friendly)

### Step 0. Start services

```powershell
cd roas-forecast-service
docker compose up -d --build
docker compose ps
```
### Step 1. Apply database schema
```powershell
docker compose run --rm migrate
```
Verify:
```powershell
docker compose exec api sh -lc "python scripts/load_csv_to_clickhouse.py --csv /app/test_task_cl.csv --table cohort_metrics_raw"
'''

### Step 2. Load CSV data (HTTP insert — recommended on Windows)

#### Option A. Load via Python loader (recommended)

Mount the directory with CSV file into the api container
(for example, via docker-compose.yml → api.volumes):

volumes:
  - "C:/Users/{root}:/data"
#### Option B

```powershell
docker cp "C:\Users\{path_to_file}\test_task_cl.csv" roas-forecast-service-api-1:/app/test_task_cl.csv
'''



```powershell
docker compose exec api sh -lc "python scripts/load_csv_to_clickhouse.py --csv /data/test_task_cl.csv --table cohort_metrics_raw"
```

Verify:

```powershell
docker compose exec clickhouse clickhouse-client --query "SELECT count() FROM roas.cohort_metrics_raw"
docker compose exec clickhouse clickhouse-client --query "SELECT min(cost), max(cost), countIf(cost > 0) FROM roas.cohort_metrics"
'''

### Step 3. Train models (inside API container)
```powershell
docker compose run --rm train

```
Artifacts schoudl be like thist 

```powershell
models/
  ├── micro_iap_latest.cbm
  ├── micro_iaa_latest.cbm
  ├── mid_iap_latest.cbm
  ├── mid_iaa_latest.cbm
  ├── macro_iap_latest.cbm
  └── macro_iaa_latest.cbm
```

### Step 4. Smoke test API
Health check

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```
Prediction example (micro level):

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/predict" `
  -ContentType "application/json" `
  -Body (@{
    level = "micro"
    target = "iap"
    opt_group_map = "opt_group_1"
    date_from = 350
    date_to = 420
  } | ConvertTo-Json)

```
### Notes

- Data source of truth: ClickHouse table roas.cohort_metrics_raw

- Serving view: roas.cohort_metrics
(adds derived fields: date_idx, cpi, cost)

- Inference safety: only D0–D7 cohort features are used (no leakage)

- Aggregation level (micro / mid / macro) is selectable per request

- Models are trained on historical cohorts and served via FastAPI.

### Entry Points
- API: src/api/app.py

- Training: src/training/train.py

- DB schema: sql/schema.sql

- Docker setup: docker-compose.yml
