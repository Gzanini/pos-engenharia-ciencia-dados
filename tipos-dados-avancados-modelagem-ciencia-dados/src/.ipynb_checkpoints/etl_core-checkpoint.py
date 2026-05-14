"""Core ETL functions for FS mix pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@dataclass
class EtlResult:
    file_name: str
    file_type: str
    rows_loaded: int
    status: str
    error_message: str = ""


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def get_pg_conn_str() -> str:
    host = _env("POSTGRES_HOST", "localhost")
    port = _env("POSTGRES_PORT", "5432")
    db = _env("POSTGRES_DB", "fs_mix")
    user = _env("POSTGRES_USER", "fs_user")
    pwd = _env("POSTGRES_PASSWORD", "fs_pass")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


def get_engine(conn_str: str | None = None) -> Engine:
    return create_engine(conn_str or get_pg_conn_str(), future=True)


def _sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_record(record: Dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, "", "null"):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except Exception:
        return None


def _to_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text_value = str(value).strip().lower()
    if text_value in {"true", "1", "sim", "s", "y", "yes"}:
        return True
    if text_value in {"false", "0", "nao", "não", "n", "no"}:
        return False
    return None


def _to_date(value: Any):
    if value in (None, "", "null"):
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except Exception:
            continue
    return None


def _read_text(file_path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return file_path.read_text(encoding=enc)
        except Exception:
            continue
    return file_path.read_text(encoding="utf-8", errors="replace")


def parse_json_records(file_path: Path) -> List[Dict[str, Any]]:
    text_data = _read_text(file_path).strip()
    if not text_data:
        return []

    try:
        loaded = json.loads(text_data)
        if isinstance(loaded, list):
            return [r for r in loaded if isinstance(r, dict)]
        if isinstance(loaded, dict):
            return [loaded]
    except Exception:
        pass

    records: List[Dict[str, Any]] = []
    for line in text_data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
        except Exception:
            continue
    return records


def parse_csv_records(file_path: Path) -> List[Dict[str, Any]]:
    text_data = _read_text(file_path)
    rows: List[Dict[str, Any]] = []
    reader = csv.DictReader(text_data.splitlines())
    for row in reader:
        rows.append({(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return rows


def _register_file(
    conn,
    file_name: str,
    file_hash: str,
    file_type: str,
    status: str,
    rows_loaded: int = 0,
    error_message: str = "",
):
    conn.execute(
        text(
            """
            INSERT INTO bronze.file_registry (file_name, file_hash, file_type, status, rows_loaded, error_message, processed_at)
            VALUES (:file_name, :file_hash, :file_type, :status, :rows_loaded, :error_message, NOW())
            ON CONFLICT (file_name) DO UPDATE SET
                file_hash = EXCLUDED.file_hash,
                file_type = EXCLUDED.file_type,
                status = EXCLUDED.status,
                rows_loaded = EXCLUDED.rows_loaded,
                error_message = EXCLUDED.error_message,
                processed_at = NOW();
            """
        ),
        {
            "file_name": file_name,
            "file_hash": file_hash,
            "file_type": file_type,
            "status": status,
            "rows_loaded": rows_loaded,
            "error_message": error_message,
        },
    )


def _already_processed(conn, file_name: str, file_hash: str) -> bool:
    row = conn.execute(
        text(
            """
            SELECT 1
            FROM bronze.file_registry
            WHERE file_name = :file_name
              AND file_hash = :file_hash
              AND status = 'SUCCESS'
            LIMIT 1;
            """
        ),
        {"file_name": file_name, "file_hash": file_hash},
    ).first()
    return row is not None


def _insert_movimentacoes(conn, source_file: str, records: List[Dict[str, Any]]) -> int:
    loaded = 0
    for idx, record in enumerate(records, start=1):
        record_hash = _hash_record(record)

        conn.execute(
            text(
                """
                INSERT INTO bronze.movimentacoes_raw (source_file, source_row, record_hash, payload)
                VALUES (:source_file, :source_row, :record_hash, CAST(:payload AS JSONB))
                ON CONFLICT (record_hash) DO NOTHING;
                """
            ),
            {
                "source_file": source_file,
                "source_row": idx,
                "record_hash": record_hash,
                "payload": json.dumps(record, ensure_ascii=False, default=str),
            },
        )

        qtd_venda = _to_decimal(record.get("qtd_venda"))
        valor_unitario = _to_decimal(record.get("valor_unitario"))
        desconto_dig = _to_decimal(record.get("valor_desconto_digitado")) or Decimal("0")
        desconto_prop = _to_decimal(record.get("valor_desconto_proporcional")) or Decimal("0")
        frete_item = _to_decimal(record.get("valor_frete_item")) or Decimal("0")

        valor_bruto = (qtd_venda or Decimal("0")) * (valor_unitario or Decimal("0"))
        valor_liquido = valor_bruto - desconto_dig - desconto_prop + frete_item

        conn.execute(
            text(
                """
                INSERT INTO silver.fato_movimentacoes (
                    record_hash, source_file, source_row, data_emissao,
                    id_produto_servico, id_produto_servico_empresa,
                    cd_cfop, descricao_cfop, cd_modelo, descricao_modelo,
                    cd_modelo_fiscal, cd_situacao, descricao_situacao,
                    direcao_estoque, tipo_transacao, id_pessoa,
                    status_item_cancelado, qtd_item_movimentacao, qtd_venda,
                    valor_unitario, valor_desconto_digitado, valor_desconto_proporcional,
                    valor_frete_item, valor_total_bruto, valor_total_liquido
                ) VALUES (
                    :record_hash, :source_file, :source_row, :data_emissao,
                    :id_produto_servico, :id_produto_servico_empresa,
                    :cd_cfop, :descricao_cfop, :cd_modelo, :descricao_modelo,
                    :cd_modelo_fiscal, :cd_situacao, :descricao_situacao,
                    :direcao_estoque, :tipo_transacao, :id_pessoa,
                    :status_item_cancelado, :qtd_item_movimentacao, :qtd_venda,
                    :valor_unitario, :valor_desconto_digitado, :valor_desconto_proporcional,
                    :valor_frete_item, :valor_total_bruto, :valor_total_liquido
                )
                ON CONFLICT (record_hash) DO NOTHING;
                """
            ),
            {
                "record_hash": record_hash,
                "source_file": source_file,
                "source_row": idx,
                "data_emissao": _to_date(record.get("data_emissao")),
                "id_produto_servico": str(record.get("id_produto_servico") or "") or None,
                "id_produto_servico_empresa": str(record.get("id_produto_servico_empresa") or "") or None,
                "cd_cfop": str(record.get("cd_cfop") or "") or None,
                "descricao_cfop": str(record.get("descricao_cfop") or "") or None,
                "cd_modelo": str(record.get("cd_modelo") or "") or None,
                "descricao_modelo": str(record.get("descricao_modelo") or "") or None,
                "cd_modelo_fiscal": str(record.get("cd_modelo_fiscal") or "") or None,
                "cd_situacao": str(record.get("cd_situacao") or "") or None,
                "descricao_situacao": str(record.get("descricao_situacao") or "") or None,
                "direcao_estoque": str(record.get("direcao_estoque") or "") or None,
                "tipo_transacao": str(record.get("tipo_transacao") or "") or None,
                "id_pessoa": str(record.get("id_pessoa") or "") or None,
                "status_item_cancelado": _to_bool(record.get("status_item_cancelado")),
                "qtd_item_movimentacao": _to_decimal(record.get("qtd_item_movimentacao")),
                "qtd_venda": qtd_venda,
                "valor_unitario": valor_unitario,
                "valor_desconto_digitado": _to_decimal(record.get("valor_desconto_digitado")),
                "valor_desconto_proporcional": _to_decimal(record.get("valor_desconto_proporcional")),
                "valor_frete_item": _to_decimal(record.get("valor_frete_item")),
                "valor_total_bruto": valor_bruto,
                "valor_total_liquido": valor_liquido,
            },
        )
        loaded += 1

    return loaded


def _insert_produtos(conn, source_file: str, records: List[Dict[str, Any]]) -> int:
    loaded = 0
    for idx, record in enumerate(records, start=1):
        record_hash = _hash_record(record)

        conn.execute(
            text(
                """
                INSERT INTO bronze.produtos_servicos_raw (source_file, source_row, record_hash, payload)
                VALUES (:source_file, :source_row, :record_hash, CAST(:payload AS JSONB))
                ON CONFLICT (record_hash) DO NOTHING;
                """
            ),
            {
                "source_file": source_file,
                "source_row": idx,
                "record_hash": record_hash,
                "payload": json.dumps(record, ensure_ascii=False, default=str),
            },
        )

        id_produto = str(record.get("id_produto_servico") or "").strip()
        if not id_produto:
            continue

        conn.execute(
            text(
                """
                INSERT INTO silver.dim_produtos_servicos (
                    id_produto_servico, cd_produto_servico, descricao, status_produto_servico,
                    pesavel, vendavel, percentual_cashback, unidade_sigla, tipo_item_descricao,
                    sub_grupo_referencia, codigo_barras, codigo_barras_tributavel,
                    id_produto_servico_empresa_referencia, id_empresa_referencia,
                    id_estoque_referencia, id_preco_referencia,
                    margem_lucro_aplicada_referencia, limite_desconto_referencia,
                    percentual_comissao_referencia, source_file
                ) VALUES (
                    :id_produto_servico, :cd_produto_servico, :descricao, :status_produto_servico,
                    :pesavel, :vendavel, :percentual_cashback, :unidade_sigla, :tipo_item_descricao,
                    :sub_grupo_referencia, :codigo_barras, :codigo_barras_tributavel,
                    :id_produto_servico_empresa_referencia, :id_empresa_referencia,
                    :id_estoque_referencia, :id_preco_referencia,
                    :margem_lucro_aplicada_referencia, :limite_desconto_referencia,
                    :percentual_comissao_referencia, :source_file
                )
                ON CONFLICT (id_produto_servico) DO UPDATE SET
                    cd_produto_servico = EXCLUDED.cd_produto_servico,
                    descricao = EXCLUDED.descricao,
                    status_produto_servico = EXCLUDED.status_produto_servico,
                    pesavel = EXCLUDED.pesavel,
                    vendavel = EXCLUDED.vendavel,
                    percentual_cashback = EXCLUDED.percentual_cashback,
                    unidade_sigla = EXCLUDED.unidade_sigla,
                    tipo_item_descricao = EXCLUDED.tipo_item_descricao,
                    sub_grupo_referencia = EXCLUDED.sub_grupo_referencia,
                    codigo_barras = EXCLUDED.codigo_barras,
                    codigo_barras_tributavel = EXCLUDED.codigo_barras_tributavel,
                    id_produto_servico_empresa_referencia = EXCLUDED.id_produto_servico_empresa_referencia,
                    id_empresa_referencia = EXCLUDED.id_empresa_referencia,
                    id_estoque_referencia = EXCLUDED.id_estoque_referencia,
                    id_preco_referencia = EXCLUDED.id_preco_referencia,
                    margem_lucro_aplicada_referencia = EXCLUDED.margem_lucro_aplicada_referencia,
                    limite_desconto_referencia = EXCLUDED.limite_desconto_referencia,
                    percentual_comissao_referencia = EXCLUDED.percentual_comissao_referencia,
                    source_file = EXCLUDED.source_file,
                    ingestion_ts = NOW();
                """
            ),
            {
                "id_produto_servico": id_produto,
                "cd_produto_servico": str(record.get("cd_produto_servico") or "") or None,
                "descricao": str(record.get("descricao") or "") or None,
                "status_produto_servico": str(record.get("status_produto_servico") or "") or None,
                "pesavel": _to_bool(record.get("pesavel")),
                "vendavel": _to_bool(record.get("vendavel")),
                "percentual_cashback": _to_decimal(record.get("percentual_cashback")),
                "unidade_sigla": str(record.get("unidade_sigla") or "") or None,
                "tipo_item_descricao": str(record.get("tipo_item_descricao") or "") or None,
                "sub_grupo_referencia": str(record.get("sub_grupo_referencia") or "") or None,
                "codigo_barras": str(record.get("codigo_barras") or "") or None,
                "codigo_barras_tributavel": str(record.get("codigo_barras_tributavel") or "") or None,
                "id_produto_servico_empresa_referencia": str(record.get("id_produto_servico_empresa_referencia") or "") or None,
                "id_empresa_referencia": str(record.get("id_empresa_referencia") or "") or None,
                "id_estoque_referencia": str(record.get("id_estoque_referencia") or "") or None,
                "id_preco_referencia": str(record.get("id_preco_referencia") or "") or None,
                "margem_lucro_aplicada_referencia": _to_decimal(record.get("margem_lucro_aplicada_referencia")),
                "limite_desconto_referencia": _to_decimal(record.get("limite_desconto_referencia")),
                "percentual_comissao_referencia": _to_decimal(record.get("percentual_comissao_referencia")),
                "source_file": source_file,
            },
        )
        loaded += 1

    return loaded


def _move_file(file_path: Path, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / file_path.name
    if destination.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = target_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
    file_path.replace(destination)


def process_file(file_path: Path, engine: Engine, processed_dir: Path, failed_dir: Path) -> EtlResult:
    file_hash = _sha256_file(file_path)
    lower_name = file_path.name.lower()

    if lower_name.startswith("movimentacoes") and file_path.suffix.lower() == ".json":
        file_type = "movimentacoes_json"
    elif lower_name.startswith("produtos_servicos") and file_path.suffix.lower() == ".csv":
        file_type = "produtos_servicos_csv"
    else:
        return EtlResult(file_name=file_path.name, file_type="ignored", rows_loaded=0, status="IGNORED")

    with engine.begin() as conn:
        if _already_processed(conn, file_path.name, file_hash):
            return EtlResult(file_name=file_path.name, file_type=file_type, rows_loaded=0, status="SKIPPED")
        _register_file(conn, file_path.name, file_hash, file_type, "RUNNING", 0, "")

    try:
        if file_type == "movimentacoes_json":
            records = parse_json_records(file_path)
        else:
            records = parse_csv_records(file_path)

        with engine.begin() as conn:
            if file_type == "movimentacoes_json":
                loaded = _insert_movimentacoes(conn, file_path.name, records)
            else:
                loaded = _insert_produtos(conn, file_path.name, records)

            _register_file(conn, file_path.name, file_hash, file_type, "SUCCESS", loaded, "")

        _move_file(file_path, processed_dir)
        return EtlResult(file_name=file_path.name, file_type=file_type, rows_loaded=loaded, status="SUCCESS")

    except Exception as exc:
        with engine.begin() as conn:
            _register_file(conn, file_path.name, file_hash, file_type, "FAILED", 0, str(exc)[:3000])
        _move_file(file_path, failed_dir)
        return EtlResult(file_name=file_path.name, file_type=file_type, rows_loaded=0, status="FAILED", error_message=str(exc))


def process_directory(
    input_dir: str | Path,
    processed_dir: str | Path,
    failed_dir: str | Path,
    engine: Engine | None = None,
) -> List[EtlResult]:
    engine = engine or get_engine()
    input_path = Path(input_dir)
    processed_path = Path(processed_dir)
    failed_path = Path(failed_dir)

    input_path.mkdir(parents=True, exist_ok=True)
    processed_path.mkdir(parents=True, exist_ok=True)
    failed_path.mkdir(parents=True, exist_ok=True)

    files = sorted([p for p in input_path.iterdir() if p.is_file()])
    results: List[EtlResult] = []

    for file_path in files:
        results.append(process_file(file_path, engine, processed_path, failed_path))

    return results


def run_once(
    input_dir: str | Path | None = None,
    processed_dir: str | Path | None = None,
    failed_dir: str | Path | None = None,
) -> List[EtlResult]:
    return process_directory(
        input_dir=input_dir or _env("INPUT_DIR", "./data/pending"),
        processed_dir=processed_dir or _env("PROCESSED_DIR", "./data/processed"),
        failed_dir=failed_dir or _env("FAILED_DIR", "./data/failed"),
        engine=get_engine(),
    )


def run_loop(
    sleep_seconds: int = 30,
    input_dir: str | Path | None = None,
    processed_dir: str | Path | None = None,
    failed_dir: str | Path | None = None,
):
    while True:
        results = run_once(input_dir=input_dir, processed_dir=processed_dir, failed_dir=failed_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] arquivos avaliados: {len(results)}")
        for result in results:
            print(f"  - {result.file_name}: {result.status} ({result.rows_loaded} linhas)")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    run_once()
