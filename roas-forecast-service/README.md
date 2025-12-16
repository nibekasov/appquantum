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




---

## Quick Start (Windows-friendly)

### Step 0. Start services

```powershell
cd roas-forecast-service
docker compose up -d --build
docker compose ps
Step 1. Apply database schema
powershell
Copy code
docker cp .\\sql\\schema.sql roas-forecast-service-clickhouse-1:/tmp/schema.sql
docker exec -it roas-forecast-service-clickhouse-1 bash -lc "clickhouse-client --multiquery < /tmp/schema.sql"
Verify:

powershell
Copy code
docker exec -it roas-forecast-service-clickhouse-1 clickhouse-client --query "SHOW DATABASES"
docker exec -it roas-forecast-service-clickhouse-1 clickhouse-client --query "SHOW TABLES FROM roas"
Step 2. Load CSV data (HTTP insert — recommended on Windows)
powershell
Copy code
curl.exe -sS `
  -H "Content-Type: text/plain" `
  --data-binary "@C:\\Users\\nibek\\Downloads\\Telegram Desktop\\test_task_cl.csv" `
  "http://localhost:8123/?query=INSERT%20INTO%20roas.cohort_metrics%20FORMAT%20CSVWithNames"
Verify:

powershell
Copy code
curl.exe -sS "http://localhost:8123/?query=SELECT%20count()%20FROM%20roas.cohort_metrics"
Step 3. Train models (inside API container)
powershell
Copy code
docker exec -it roas-forecast-service-api-1 python -m src.training.train
Verify artifacts:

powershell
Copy code
docker exec -it roas-forecast-service-api-1 ls -lah /app/models
Expected:

python-repl
Copy code
micro_iap_latest.cbm
micro_iaa_latest.cbm
mid_iap_latest.cbm
macro_iap_latest.cbm
...
Step 4. Smoke test API
Health check

powershell
Copy code
curl.exe http://localhost:8000/health
Prediction (macro level)

powershell
Copy code
curl.exe -X POST "http://localhost:8000/predict" `
  -H "Content-Type: application/json" `
  -d "{ `\"level`\": `\"macro`\", `\"target`\": `\"iap`\", `\"date_from`\": 251, `\"date_to`\": 257 }"
Notes
Models are trained on historical cohorts and served via FastAPI.

Inference strictly uses D0–D7 features only.

Aggregation level (micro / mid / macro) can be selected per request.

ClickHouse is used as a source of truth for cohort metrics.

Entry Points
API: src/api/app.py

Training: src/training/train.py

DB schema: sql/schema.sql

Docker setup: docker-compose.yml
