.PHONY: up down logs load train

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

load:
	python scripts/load_csv_to_clickhouse.py --csv ../test_task_cl.csv

train:
	python -m src.training.train
