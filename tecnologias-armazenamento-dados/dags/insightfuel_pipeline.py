from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task
from airflow.models import Variable
from airflow.operators.python import get_current_context
from airflow.utils.task_group import TaskGroup

from insightfuel.config import load_settings
from insightfuel.pipeline import (
    archive_bronze,
    generate_gold,
    ingest_bronze,
    process_silver,
    validate_gold,
    validate_layout,
    validate_quality,
)


SOURCES = ("anp", "populacao", "pib", "ipca")


def airflow_settings():
    return load_settings(lambda name, default=None: Variable.get(name, default_var=default))


def current_run_id() -> str:
    return str(get_current_context()["run_id"])


@dag(
    dag_id="insightfuel_pipeline",
    description="ANP + IBGE -> GCS/Bronze -> BigQuery/Silver -> BigQuery/Gold",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["insightfuel", "anp", "ibge", "gcp"],
)
def insightfuel_pipeline():
    @task(retries=1)
    def validar_layout_fonte(source: str) -> list[str]:
        return validate_layout(airflow_settings(), source, current_run_id())

    @task(retries=2)
    def ingerir_fonte(source: str, validated_files: list[str]) -> list[str]:
        return ingest_bronze(
            airflow_settings(), source, current_run_id(), validated_files
        )

    @task(retries=1)
    def processar_fonte(source: str, bronze_objects: list[str]) -> int:
        return process_silver(
            airflow_settings(), source, current_run_id(), bronze_objects
        )

    @task(task_id="validar_silver")
    def validar_silver(_source_counts: list[int]) -> dict[str, int]:
        return validate_quality(airflow_settings(), current_run_id())

    @task(task_id="gerar_gold", retries=1)
    def gerar_gold(_silver_metrics: dict[str, int]) -> int:
        return generate_gold(airflow_settings(), current_run_id())

    @task(task_id="validar_gold")
    def validar_gold_task(_gold_count: int) -> dict[str, int]:
        return validate_gold(airflow_settings(), current_run_id())

    @task(task_id="arquivar_bronze")
    def arquivar_bronze_task(
        source_objects: dict[str, list[str]], _gold_metrics: dict[str, int]
    ) -> dict[str, list[str]]:
        return archive_bronze(
            airflow_settings(), current_run_id(), source_objects
        )

    branches = {}
    for source in SOURCES:
        with TaskGroup(group_id=source):
            validated = validar_layout_fonte.override(task_id="validar_layout")(source)
            bronze = ingerir_fonte.override(task_id="ingestao_bronze")(source, validated)
            silver = processar_fonte.override(task_id="processar_silver")(source, bronze)
            branches[source] = {"objects": bronze, "count": silver}

    silver_quality = validar_silver([branch["count"] for branch in branches.values()])
    gold_count = gerar_gold(silver_quality)
    gold_quality = validar_gold_task(gold_count)
    arquivar_bronze_task(
        {source: branch["objects"] for source, branch in branches.items()},
        gold_quality,
    )


insightfuel_pipeline()
