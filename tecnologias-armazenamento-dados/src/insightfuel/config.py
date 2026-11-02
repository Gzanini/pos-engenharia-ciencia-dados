from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


VariableGetter = Callable[[str, str | None], str | None]


@dataclass(frozen=True)
class Settings:
    input_root: Path
    project_id: str
    bucket: str
    location: str
    silver_dataset: str
    gold_dataset: str
    control_dataset: str
    silver_table: str
    population_table: str
    pib_table: str
    ipca_table: str
    gold_table: str
    control_table: str
    bronze_root: str
    credentials_path: str | None

    def validate(self) -> "Settings":
        missing = [
            name
            for name, value in {
                "insightfuel_input_root": str(self.input_root) if str(self.input_root) != "." else "",
                "insightfuel_gcp_project_id": self.project_id,
                "insightfuel_gcs_bucket": self.bucket,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(f"Airflow Variables obrigatórias: {', '.join(missing)}")
        return self

    def source_dir(self, source: str) -> Path:
        return self.input_root / source

    def export_google_environment(self) -> None:
        """Expose only variables understood by Google client libraries."""
        if self.project_id:
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
        if self.credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path


def _environment_getter(name: str, default: str | None = None) -> str | None:
    return os.getenv(name.upper(), default)


def load_settings(getter: VariableGetter | None = None) -> Settings:
    """Load the GCP configuration from Airflow Variables."""
    get = getter or _environment_getter
    settings = Settings(
        input_root=Path(str(get("insightfuel_input_root", ""))),
        project_id=str(get("insightfuel_gcp_project_id", "")),
        bucket=str(get("insightfuel_gcs_bucket", "")),
        location=str(get("insightfuel_gcp_location", "southamerica-east1")),
        silver_dataset=str(get("insightfuel_bq_silver_dataset", "insightfuel_silver")),
        gold_dataset=str(get("insightfuel_bq_gold_dataset", "insightfuel_gold")),
        control_dataset=str(get("insightfuel_bq_control_dataset", "insightfuel_control")),
        silver_table=str(get("insightfuel_bq_silver_table", "silver_precos_anp")),
        population_table=str(get("insightfuel_bq_population_table", "silver_populacao_ibge")),
        pib_table=str(get("insightfuel_bq_pib_table", "silver_pib_municipios_ibge")),
        ipca_table=str(get("insightfuel_bq_ipca_table", "silver_ipca_ibge")),
        gold_table=str(get("insightfuel_bq_gold_table", "gold_precos_combustiveis_mensal")),
        control_table=str(get("insightfuel_bq_control_table", "ingestion_events")),
        bronze_root=str(get("insightfuel_bronze_root", "bronze")),
        credentials_path=get("insightfuel_google_credentials_path", None),
    )
    return settings.validate()

