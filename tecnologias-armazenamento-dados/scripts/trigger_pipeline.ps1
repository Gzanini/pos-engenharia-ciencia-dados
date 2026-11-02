$ErrorActionPreference = "Stop"

docker compose exec -T airflow-scheduler airflow dags unpause insightfuel_pipeline
docker compose exec -T airflow-scheduler airflow dags trigger insightfuel_pipeline

