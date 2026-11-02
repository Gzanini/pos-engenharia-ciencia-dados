$ErrorActionPreference = "Stop"

docker info | Out-Null
docker compose run --rm airflow-init
docker compose up -d --build airflow-webserver airflow-scheduler
docker compose ps

