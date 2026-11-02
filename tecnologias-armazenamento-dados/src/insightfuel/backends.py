from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings


SOURCE_SCHEMAS = {
    "anp": [
        ("cnpj_revenda", "STRING"), ("estabelecimento", "STRING"), ("uf", "STRING"),
        ("municipio", "STRING"), ("produto", "STRING"), ("data_coleta", "DATE"),
        ("valor_venda", "FLOAT64"), ("bandeira", "STRING"),
    ],
    "populacao": [
        ("codigo_municipio", "STRING"), ("municipio", "STRING"), ("uf", "STRING"),
        ("ano", "INT64"), ("populacao", "INT64"),
    ],
    "pib": [
        ("codigo_municipio", "STRING"), ("municipio", "STRING"), ("uf", "STRING"),
        ("ano", "INT64"), ("pib", "FLOAT64"), ("pib_per_capita", "FLOAT64"),
    ],
    "ipca": [
        ("ano", "INT64"), ("mes", "INT64"), ("numero_indice", "FLOAT64"),
        ("variacao_percentual", "FLOAT64"),
    ],
}


class GcpBackend:
    """Google Cloud Storage, BigQuery and ingestion-control operations."""

    def __init__(self, settings: Settings):
        settings.export_google_environment()
        try:
            from google.cloud import bigquery, storage
        except ImportError as exc:
            raise RuntimeError("Instale as dependências GCP do projeto") from exc
        self.settings = settings
        self.bigquery = bigquery
        self.storage_client = storage.Client(project=settings.project_id)
        self.bq_client = bigquery.Client(project=settings.project_id, location=settings.location)

    def local_files(self, source: str) -> list[Path]:
        source_dir = self.settings.source_dir(source)
        if not source_dir.is_dir():
            raise FileNotFoundError(f"Pasta da fonte não encontrada: {source_dir}")
        allowed = {
            "anp": {".csv"},
            "populacao": {".csv", ".xls", ".xlsx"},
            "pib": {".csv", ".xlsx"},
            "ipca": {".csv", ".xls", ".xlsx"},
        }[source]
        files = sorted(
            path for path in source_dir.iterdir()
            if path.is_file() and path.suffix.lower() in allowed
        )
        if not files:
            raise FileNotFoundError(f"Nenhum arquivo compatível encontrado em: {source_dir}")
        return files

    def upload_files(
        self, source: str, run_id: str, files: list[Path], status: str = "incoming"
    ) -> list[str]:
        safe_run_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", run_id)
        bucket = self.storage_client.bucket(self.settings.bucket)
        uploaded = []
        for path in files:
            object_name = (
                f"{self.settings.bronze_root.rstrip('/')}/{source}/{status}/"
                f"{safe_run_id}/{path.name}"
            )
            bucket.blob(object_name).upload_from_filename(path)
            uploaded.append(f"gs://{self.settings.bucket}/{object_name}")
        return uploaded

    def read_objects(self, object_uris: list[str]) -> list[tuple[str, bytes]]:
        if not object_uris:
            raise ValueError("Nenhum objeto Bronze informado")
        expected_prefix = f"gs://{self.settings.bucket}/"
        bucket = self.storage_client.bucket(self.settings.bucket)
        files = []
        for uri in sorted(object_uris):
            if not uri.startswith(expected_prefix):
                raise ValueError(f"Objeto fora do bucket configurado: {uri}")
            name = uri.removeprefix(expected_prefix)
            files.append((name, bucket.blob(name).download_as_bytes()))
        return files

    def move_objects(self, object_uris: list[str], destination_status: str) -> list[str]:
        expected_prefix = f"gs://{self.settings.bucket}/"
        bucket = self.storage_client.bucket(self.settings.bucket)
        moved = []
        for uri in object_uris:
            if not uri.startswith(expected_prefix):
                raise ValueError(f"Objeto fora do bucket configurado: {uri}")
            source_name = uri.removeprefix(expected_prefix)
            destination_name = source_name.replace("/incoming/", f"/{destination_status}/", 1)
            source_blob = bucket.blob(source_name)
            destination_blob = bucket.blob(destination_name)
            if not source_blob.exists():
                if destination_blob.exists():
                    moved.append(f"gs://{self.settings.bucket}/{destination_name}")
                    continue
                raise FileNotFoundError(f"Objeto de origem e destino não encontrados: {uri}")
            bucket.copy_blob(source_blob, bucket, destination_name)
            source_blob.delete()
            moved.append(f"gs://{self.settings.bucket}/{destination_name}")
        return moved

    def replace_source(self, source: str, rows: list[dict[str, object]]) -> int:
        table = {
            "anp": self.settings.silver_table,
            "populacao": self.settings.population_table,
            "pib": self.settings.pib_table,
            "ipca": self.settings.ipca_table,
        }[source]
        return self._replace(self.settings.silver_dataset, table, rows, SOURCE_SCHEMAS[source])

    def validate_silver(self) -> dict[str, int]:
        tables = {
            "anp": self.settings.silver_table,
            "populacao": self.settings.population_table,
            "pib": self.settings.pib_table,
            "ipca": self.settings.ipca_table,
        }
        required_fields = {
            "anp": {
                "cnpj_revenda": "string", "estabelecimento": "string", "uf": "string",
                "municipio": "string", "produto": "string", "data_coleta": "value",
                "valor_venda": "value", "bandeira": "string",
            },
            "populacao": {
                "codigo_municipio": "string", "municipio": "string", "uf": "string",
                "ano": "value", "populacao": "value",
            },
            "pib": {
                "codigo_municipio": "string", "municipio": "string", "uf": "string",
                "ano": "value", "pib": "value", "pib_per_capita": "value",
            },
            "ipca": {
                "ano": "value", "mes": "value", "numero_indice": "value",
                "variacao_percentual": "value",
            },
        }
        metrics = {}
        for source, table_name in tables.items():
            table = self._table_id(self.settings.silver_dataset, table_name)
            invalid_checks = [
                f"{field} IS NULL" + (f" OR {field} = ''" if kind == "string" else "")
                for field, kind in required_fields[source].items()
            ]
            invalid_expression = " OR ".join(f"({check})" for check in invalid_checks)
            query = (
                f"SELECT COUNT(*) AS n, "
                f"COUNTIF({invalid_expression}) AS invalid FROM `{table}`"
            )
            row = next(iter(self.bq_client.query(query).result()))
            count = int(row.n)
            if count == 0:
                raise ValueError(f"Silver vazia para {source}")
            if int(row.invalid):
                raise ValueError(
                    f"Silver {source} possui {int(row.invalid)} registros com campos obrigatórios vazios"
                )
            metrics[source] = count
        return metrics

    def generate_gold(self) -> int:
        silver = self.settings.silver_dataset
        project = self.settings.project_id
        query = f"""
        WITH precos AS (
          SELECT EXTRACT(YEAR FROM data_coleta) AS ano,
                 EXTRACT(MONTH FROM data_coleta) AS mes,
                 uf, municipio, produto,
                 AVG(valor_venda) AS preco_medio,
                 MIN(valor_venda) AS preco_minimo,
                 MAX(valor_venda) AS preco_maximo,
                 STDDEV_POP(valor_venda) AS desvio_padrao_preco,
                 COUNT(*) AS quantidade_observacoes
          FROM `{project}.{silver}.{self.settings.silver_table}`
          GROUP BY 1,2,3,4,5
        ), populacao AS (
          SELECT * EXCEPT(rn) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY codigo_municipio ORDER BY ano DESC) rn
            FROM `{project}.{silver}.{self.settings.population_table}`
          ) WHERE rn = 1
        ), pib AS (
          SELECT * EXCEPT(rn) FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY codigo_municipio ORDER BY ano DESC) rn
            FROM `{project}.{silver}.{self.settings.pib_table}`
          ) WHERE rn = 1
        )
        SELECT p.*, pop.codigo_municipio, pop.populacao,
               pib.pib, pib.pib_per_capita,
               ipca.numero_indice AS ipca_numero_indice,
               ipca.variacao_percentual AS ipca_variacao_percentual
        FROM precos p
        LEFT JOIN populacao pop ON p.uf = pop.uf AND p.municipio = pop.municipio
        LEFT JOIN pib ON pop.codigo_municipio = pib.codigo_municipio
        LEFT JOIN `{project}.{silver}.{self.settings.ipca_table}` ipca
          ON p.ano = ipca.ano AND p.mes = ipca.mes
        """
        destination = self._table_id(self.settings.gold_dataset, self.settings.gold_table)
        config = self.bigquery.QueryJobConfig(
            destination=destination,
            write_disposition=self.bigquery.WriteDisposition.WRITE_TRUNCATE,
            use_legacy_sql=False,
        )
        self.bq_client.query(query, job_config=config).result()
        return int(next(iter(self.bq_client.query(f"SELECT COUNT(*) n FROM `{destination}`").result())).n)

    def validate_gold(self) -> dict[str, int]:
        table = self._table_id(self.settings.gold_dataset, self.settings.gold_table)
        query = f"""
        SELECT COUNT(*) AS row_count,
          COUNTIF(preco_minimo > preco_medio OR preco_medio > preco_maximo
                  OR quantidade_observacoes <= 0) AS invalid,
          COUNTIF(codigo_municipio IS NULL OR codigo_municipio = '') AS without_municipality,
          COUNTIF(populacao IS NULL) AS without_population,
          COUNTIF(pib IS NULL OR pib_per_capita IS NULL) AS without_pib,
          COUNTIF(ipca_numero_indice IS NULL) AS without_ipca
        FROM `{table}`
        """
        result = next(iter(self.bq_client.query(query).result()))
        metrics = {
            "rows": int(result.row_count),
            "invalid": int(result.invalid),
            "without_municipality": int(result.without_municipality),
            "without_population": int(result.without_population),
            "without_pib": int(result.without_pib),
            "without_ipca": int(result.without_ipca),
        }
        critical_failures = (
            metrics["invalid"]
            + metrics["without_municipality"]
            + metrics["without_population"]
            + metrics["without_pib"]
            + metrics["without_ipca"]
        )
        if metrics["rows"] == 0 or critical_failures:
            raise ValueError(f"Qualidade Gold reprovada: {json.dumps(metrics)}")
        return metrics

    def record_event(
        self,
        run_id: str,
        source: str,
        stage: str,
        status: str,
        file_name: str | None = None,
        object_uri: str | None = None,
        row_count: int | None = None,
        details: str | None = None,
    ) -> None:
        table = self._table_id(self.settings.control_dataset, self.settings.control_table)
        row = {
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "source": source,
            "stage": stage,
            "status": status,
            "file_name": file_name,
            "object_uri": object_uri,
            "row_count": row_count,
            "event_ts": datetime.now(timezone.utc).isoformat(),
            "details": details[:1000] if details else None,
        }
        errors = self.bq_client.insert_rows_json(table, [row])
        if errors:
            raise RuntimeError(f"Falha ao registrar controle: {errors}")

    def _replace(
        self,
        dataset: str,
        table: str,
        rows: list[dict[str, object]],
        schema: list[tuple[str, str]],
    ) -> int:
        table_id = self._table_id(dataset, table)
        config = self.bigquery.LoadJobConfig(
            write_disposition=self.bigquery.WriteDisposition.WRITE_TRUNCATE,
            schema=[self.bigquery.SchemaField(name, field_type) for name, field_type in schema],
        )
        self.bq_client.load_table_from_json(rows, table_id, job_config=config).result()
        return len(rows)

    def _table_id(self, dataset: str, table: str) -> str:
        return f"{self.settings.project_id}.{dataset}.{table}"
