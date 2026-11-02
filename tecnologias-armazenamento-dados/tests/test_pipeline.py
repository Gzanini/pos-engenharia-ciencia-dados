from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from insightfuel.backends import GcpBackend
from insightfuel.config import Settings, load_settings
from insightfuel.pipeline import archive_bronze, validate_layout
from insightfuel.transform import normalize_text, read_and_clean_source_files


SAMPLES = {
    "anp": """CNPJ da Revenda;Revenda;Estado - Sigla;Município;Produto;Data da Coleta;Valor de Venda;Bandeira
12.345.678/0001-90;POSTO A;SP;Campinas;GASOLINA;01/08/2026;6,19;BRANCA
98.765.432/0001-10;POSTO B;SP;Campinas;GASOLINA;08/08/2026;6,39;IPIRANGA
12.345.678/0001-90;POSTO A;SP;Campinas;GASOLINA;01/08/2026;6,19;BRANCA
""",
    "populacao": """codigo_municipio;municipio;uf;ano;populacao
3509502;Campinas;SP;2026;1213000
3303302;Niterói;RJ;2026;516000
""",
    "pib": """codigo_municipio;municipio;uf;ano;pib;pib_per_capita
3509502;Campinas;SP;2023;91500000,00;75200,00
3303302;Niterói;RJ;2023;32000000,00;62000,00
""",
    "ipca": """ano;mes;numero_indice;variacao_percentual
2026;8;7250,10;0,35
""",
}


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.settings = Settings(
            input_root=self.root,
            project_id="projeto-teste",
            bucket="bucket-teste",
            location="southamerica-east1",
            silver_dataset="insightfuel_silver",
            gold_dataset="insightfuel_gold",
            control_dataset="insightfuel_control",
            silver_table="silver_precos_anp",
            population_table="silver_populacao_ibge",
            pib_table="silver_pib_municipios_ibge",
            ipca_table="silver_ipca_ibge",
            gold_table="gold_precos_combustiveis_mensal",
            control_table="ingestion_events",
            bronze_root="bronze",
            credentials_path=None,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_all_source_layouts(self):
        expected = {"anp": 2, "populacao": 2, "pib": 2, "ipca": 1}
        for source, sample in SAMPLES.items():
            rows = read_and_clean_source_files(source, [(f"{source}.csv", sample.encode())])
            self.assertEqual(len(rows), expected[source])

    def test_municipality_normalization_matches_anp_and_ibge(self):
        self.assertEqual(normalize_text("Sant'Ana do Livramento"), "SANTANA DO LIVRAMENTO")
        self.assertEqual(normalize_text("Santana do Livramento"), "SANTANA DO LIVRAMENTO")
        self.assertEqual(normalize_text("Ji-Paraná"), "JI PARANA")
        self.assertEqual(normalize_text("Santa Bárbara d'Oeste"), "SANTA BARBARA DOESTE")

    def test_missing_required_column_fails(self):
        invalid = SAMPLES["populacao"].replace(";populacao", "")
        with self.assertRaisesRegex(ValueError, "populacao"):
            read_and_clean_source_files("populacao", [("invalid.csv", invalid.encode())])

    def test_multiple_anp_prices_for_same_station_day_are_preserved(self):
        conflict = SAMPLES["anp"].replace(
            "98.765.432/0001-10;POSTO B;SP;Campinas;GASOLINA;08/08/2026;6,39;IPIRANGA",
            "12.345.678/0001-90;POSTO A;SP;Campinas;GASOLINA;01/08/2026;6,29;BRANCA",
        )
        rows = read_and_clean_source_files("anp", [("observations.csv", conflict.encode())])
        self.assertEqual(len(rows), 2)
        self.assertEqual(sorted(row["valor_venda"] for row in rows), [6.19, 6.29])

    def test_airflow_variables_load_all_tables(self):
        values = {
            "insightfuel_input_root": "/opt/airflow/input",
            "insightfuel_gcp_project_id": "projeto-teste",
            "insightfuel_gcs_bucket": "bucket-teste",
        }
        settings = load_settings(lambda name, default=None: values.get(name, default))
        self.assertEqual(settings.population_table, "silver_populacao_ibge")
        self.assertEqual(settings.control_dataset, "insightfuel_control")

    def test_bigquery_source_load_uses_schema_and_truncate(self):
        backend = object.__new__(GcpBackend)
        backend.settings = self.settings
        backend.bigquery = FakeBigQueryModule()
        backend.bq_client = FakeBigQueryClient()
        rows = read_and_clean_source_files("populacao", [("pop.csv", SAMPLES["populacao"].encode())])
        self.assertEqual(backend.replace_source("populacao", rows), 2)
        table_id, _, config = backend.bq_client.last_load
        self.assertEqual(table_id, "projeto-teste.insightfuel_silver.silver_populacao_ibge")
        self.assertEqual(config.write_disposition, "WRITE_TRUNCATE")
        self.assertEqual({field.name: field.field_type for field in config.schema}["populacao"], "INT64")

    def test_invalid_layout_goes_to_rejected_without_incoming_upload(self):
        source_dir = self.root / "populacao"
        source_dir.mkdir()
        (source_dir / "invalid.csv").write_text(
            SAMPLES["populacao"].replace(";populacao", ""), encoding="utf-8"
        )
        backend = FakePipelineBackend(self.root)

        with self.assertRaisesRegex(ValueError, "populacao"):
            validate_layout(self.settings, "populacao", "run-invalid", backend)

        self.assertEqual(backend.upload_statuses, ["rejected"])
        self.assertEqual(backend.events[0]["stage"], "layout")
        self.assertEqual(backend.events[0]["status"], "rejected")

    def test_archive_records_destination_uri(self):
        backend = FakePipelineBackend(self.root)
        incoming = "gs://bucket-teste/bronze/anp/incoming/run-1/anp.csv"
        result = archive_bronze(
            self.settings, "run-1", {"anp": [incoming]}, backend
        )

        expected = "gs://bucket-teste/bronze/anp/archive/run-1/anp.csv"
        self.assertEqual(result, {"anp": [expected]})
        self.assertEqual(backend.events[0]["object_uri"], expected)


class FakeSchemaField:
    def __init__(self, name: str, field_type: str):
        self.name = name
        self.field_type = field_type


class FakeLoadJobConfig:
    def __init__(self, write_disposition: str, schema):
        self.write_disposition = write_disposition
        self.schema = schema


class FakeBigQueryModule:
    class WriteDisposition:
        WRITE_TRUNCATE = "WRITE_TRUNCATE"

    SchemaField = FakeSchemaField
    LoadJobConfig = FakeLoadJobConfig


class FakeJob:
    def result(self):
        return None


class FakeBigQueryClient:
    def __init__(self):
        self.last_load = None

    def load_table_from_json(self, rows, table_id, job_config):
        self.last_load = (table_id, rows, job_config)
        return FakeJob()


class FakePipelineBackend:
    def __init__(self, root: Path):
        self.root = root
        self.upload_statuses = []
        self.events = []

    def local_files(self, source: str):
        return sorted((self.root / source).glob("*.csv"))

    def upload_files(self, source, run_id, files, status="incoming"):
        self.upload_statuses.append(status)
        return [f"gs://bucket-teste/bronze/{source}/{status}/{run_id}/{path.name}" for path in files]

    def move_objects(self, uris, destination_status):
        return [uri.replace("/incoming/", f"/{destination_status}/", 1) for uri in uris]

    def record_event(self, **kwargs):
        self.events.append(kwargs)


if __name__ == "__main__":
    unittest.main()
