# ROAS Forecast Service (D7 → D90)

Production-style skeleton to train and serve cohort-level ROAS forecasts.

- Targets: `iap_roas_d90`, `iaa_roas_d90`
- Inference uses only D0–D7 signals (no leakage)
- Levels: micro / mid / macro

See:
- `docker-compose.yml`
- `src/api/app.py`
- `src/training/train.py`
- `scripts/load_csv_to_clickhouse.py`
- `sql/schema.sql`
