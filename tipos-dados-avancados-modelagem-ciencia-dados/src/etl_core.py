"""Funcoes centrais de ETL para o pipeline de mix de produtos."""

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
from typing import Any, Dict, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# Finalidade: Estrutura o retorno do processamento de um arquivo.
@dataclass
class ResultadoEtl:
    file_name: str
    file_type: str
    rows_loaded: int
    status: str
    error_message: str = ""


# Finalidade: Le variaveis de ambiente com valor padrao.
def _ler_variavel_ambiente(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# Finalidade: Monta a string de conexao com o PostgreSQL.
def obter_string_conexao_postgres() -> str:
    host = _ler_variavel_ambiente("POSTGRES_HOST", "localhost")
    port = _ler_variavel_ambiente("POSTGRES_PORT", "5432")
    db = _ler_variavel_ambiente("POSTGRES_DB", "fs_mix")
    user = _ler_variavel_ambiente("POSTGRES_USER", "fs_user")
    pwd = _ler_variavel_ambiente("POSTGRES_PASSWORD", "fs_pass")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


# Finalidade: Cria engine SQLAlchemy para acesso ao banco.
def obter_engine(conn_str: str | None = None) -> Engine:
    return create_engine(conn_str or obter_string_conexao_postgres(), future=True)


# Finalidade: Calcula hash SHA-256 do arquivo para rastreabilidade.
def _calcular_hash_arquivo(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Finalidade: Gera hash estavel de um registro de dados.
def _gerar_hash_registro(record: Dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Finalidade: Converte valores numericos para Decimal de forma segura.
def _para_decimal(value: Any) -> Decimal | None:
    if value in (None, "", "null"):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except Exception:
        return None


# Finalidade: Converte textos comuns para valores booleanos.
def _para_booleano(value: Any) -> bool | None:
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


# Finalidade: Converte texto de data para objeto date.
def _para_data(value: Any):
    if value in (None, "", "null"):
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except Exception:
            continue
    return None


# Finalidade: Le arquivo texto com fallback de encodings.
def _ler_texto(file_path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return file_path.read_text(encoding=enc)
        except Exception:
            continue
    return file_path.read_text(encoding="utf-8", errors="replace")


# Finalidade: Carrega registros a partir de JSON array, objeto ou JSONL.
def ler_registros_json(file_path: Path) -> List[Dict[str, Any]]:
    text_data = _ler_texto(file_path).strip()
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


# Finalidade: Carrega registros de CSV e normaliza campos.
def ler_registros_csv(file_path: Path) -> List[Dict[str, Any]]:
    text_data = _ler_texto(file_path)
    rows: List[Dict[str, Any]] = []
    reader = csv.DictReader(text_data.splitlines())
    for row in reader:
        rows.append({(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return rows


# Finalidade: Registra status de processamento no file_registry.
def _registrar_arquivo(
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


# Finalidade: Carrega movimentacoes no bronze e faz upsert na fato silver.
def _carregar_movimentacoes(conn, source_file: str, records: List[Dict[str, Any]]) -> int:
    loaded = 0
    for idx, record in enumerate(records, start=1):
        record_hash = _gerar_hash_registro(record)

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

        qtd_venda = _para_decimal(record.get("qtd_venda"))
        valor_unitario = _para_decimal(record.get("valor_unitario"))
        desconto_dig = _para_decimal(record.get("valor_desconto_digitado")) or Decimal("0")
        desconto_prop = _para_decimal(record.get("valor_desconto_proporcional")) or Decimal("0")
        frete_item = _para_decimal(record.get("valor_frete_item")) or Decimal("0")

        valor_bruto = (qtd_venda or Decimal("0")) * (valor_unitario or Decimal("0"))
        valor_liquido = valor_bruto - desconto_dig - desconto_prop + frete_item

        conn.execute(
            text(
                """
                INSERT INTO silver.fato_movimentacoes (
                    record_hash, source_file, source_row, data_emissao,
                    id_movimentacao,
                    id_produto_servico, id_produto_servico_empresa,
                    cd_cfop, descricao_cfop, cd_modelo, descricao_modelo,
                    cd_modelo_fiscal, cd_situacao, descricao_situacao,
                    direcao_estoque, tipo_transacao, id_pessoa,
                    status_item_cancelado, qtd_item_movimentacao, qtd_venda,
                    valor_unitario, valor_desconto_digitado, valor_desconto_proporcional,
                    valor_frete_item, valor_total_bruto, valor_total_liquido
                ) VALUES (
                    :record_hash, :source_file, :source_row, :data_emissao,
                    :id_movimentacao,
                    :id_produto_servico, :id_produto_servico_empresa,
                    :cd_cfop, :descricao_cfop, :cd_modelo, :descricao_modelo,
                    :cd_modelo_fiscal, :cd_situacao, :descricao_situacao,
                    :direcao_estoque, :tipo_transacao, :id_pessoa,
                    :status_item_cancelado, :qtd_item_movimentacao, :qtd_venda,
                    :valor_unitario, :valor_desconto_digitado, :valor_desconto_proporcional,
                    :valor_frete_item, :valor_total_bruto, :valor_total_liquido
                )
                ON CONFLICT (id_movimentacao, id_produto_servico, id_pessoa) DO UPDATE SET
                    record_hash = EXCLUDED.record_hash,
                    source_file = EXCLUDED.source_file,
                    source_row = EXCLUDED.source_row,
                    data_emissao = EXCLUDED.data_emissao,
                    id_produto_servico_empresa = EXCLUDED.id_produto_servico_empresa,
                    cd_cfop = EXCLUDED.cd_cfop,
                    descricao_cfop = EXCLUDED.descricao_cfop,
                    cd_modelo = EXCLUDED.cd_modelo,
                    descricao_modelo = EXCLUDED.descricao_modelo,
                    cd_modelo_fiscal = EXCLUDED.cd_modelo_fiscal,
                    cd_situacao = EXCLUDED.cd_situacao,
                    descricao_situacao = EXCLUDED.descricao_situacao,
                    direcao_estoque = EXCLUDED.direcao_estoque,
                    tipo_transacao = EXCLUDED.tipo_transacao,
                    status_item_cancelado = EXCLUDED.status_item_cancelado,
                    qtd_item_movimentacao = EXCLUDED.qtd_item_movimentacao,
                    qtd_venda = EXCLUDED.qtd_venda,
                    valor_unitario = EXCLUDED.valor_unitario,
                    valor_desconto_digitado = EXCLUDED.valor_desconto_digitado,
                    valor_desconto_proporcional = EXCLUDED.valor_desconto_proporcional,
                    valor_frete_item = EXCLUDED.valor_frete_item,
                    valor_total_bruto = EXCLUDED.valor_total_bruto,
                    valor_total_liquido = EXCLUDED.valor_total_liquido,
                    ingestion_ts = NOW();
                """
            ),
            {
                "record_hash": record_hash,
                "source_file": source_file,
                "source_row": idx,
                "data_emissao": _para_data(record.get("data_emissao")),
                "id_movimentacao": str(record.get("id_movimentacao") or ""),
                "id_produto_servico": str(record.get("id_produto_servico") or ""),
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
                "id_pessoa": str(record.get("id_pessoa") or ""),
                "status_item_cancelado": _para_booleano(record.get("status_item_cancelado")),
                "qtd_item_movimentacao": _para_decimal(record.get("qtd_item_movimentacao")),
                "qtd_venda": qtd_venda,
                "valor_unitario": valor_unitario,
                "valor_desconto_digitado": _para_decimal(record.get("valor_desconto_digitado")),
                "valor_desconto_proporcional": _para_decimal(record.get("valor_desconto_proporcional")),
                "valor_frete_item": _para_decimal(record.get("valor_frete_item")),
                "valor_total_bruto": valor_bruto,
                "valor_total_liquido": valor_liquido,
            },
        )
        loaded += 1

    return loaded


# Finalidade: Carrega produtos no bronze e faz upsert na dimensao silver.
def _carregar_produtos(conn, source_file: str, records: List[Dict[str, Any]]) -> int:
    loaded = 0
    for idx, record in enumerate(records, start=1):
        record_hash = _gerar_hash_registro(record)

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
                "pesavel": _para_booleano(record.get("pesavel")),
                "vendavel": _para_booleano(record.get("vendavel")),
                "percentual_cashback": _para_decimal(record.get("percentual_cashback")),
                "unidade_sigla": str(record.get("unidade_sigla") or "") or None,
                "tipo_item_descricao": str(record.get("tipo_item_descricao") or "") or None,
                "sub_grupo_referencia": str(record.get("sub_grupo_referencia") or "") or None,
                "codigo_barras": str(record.get("codigo_barras") or "") or None,
                "codigo_barras_tributavel": str(record.get("codigo_barras_tributavel") or "") or None,
                "id_produto_servico_empresa_referencia": str(record.get("id_produto_servico_empresa_referencia") or "") or None,
                "id_empresa_referencia": str(record.get("id_empresa_referencia") or "") or None,
                "id_estoque_referencia": str(record.get("id_estoque_referencia") or "") or None,
                "id_preco_referencia": str(record.get("id_preco_referencia") or "") or None,
                "margem_lucro_aplicada_referencia": _para_decimal(record.get("margem_lucro_aplicada_referencia")),
                "limite_desconto_referencia": _para_decimal(record.get("limite_desconto_referencia")),
                "percentual_comissao_referencia": _para_decimal(record.get("percentual_comissao_referencia")),
                "source_file": source_file,
            },
        )
        loaded += 1

    return loaded


# Finalidade: Move arquivo para pasta de destino evitando colisao de nome.
def _mover_arquivo(file_path: Path, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / file_path.name
    if destination.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = target_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
    file_path.replace(destination)


# Finalidade: Processa um arquivo individual e controla sucesso/erro.
def processar_arquivo(file_path: Path, engine: Engine, processed_dir: Path, failed_dir: Path) -> ResultadoEtl:
    file_hash = _calcular_hash_arquivo(file_path)
    lower_name = file_path.name.lower()

    if lower_name.startswith("movimentacoes") and file_path.suffix.lower() == ".json":
        file_type = "movimentacoes_json"
    elif lower_name.startswith("produtos_servicos") and file_path.suffix.lower() == ".csv":
        file_type = "produtos_servicos_csv"
    else:
        file_type = "unsupported"
        error_message = "Padrao de nome de arquivo nao suportado. Esperado: movimentacoes*.json ou produtos_servicos*.csv."
        with engine.begin() as conn:
            _registrar_arquivo(conn, file_path.name, file_hash, file_type, "FAILED", 0, error_message)
        _mover_arquivo(file_path, failed_dir)
        return ResultadoEtl(
            file_name=file_path.name,
            file_type=file_type,
            rows_loaded=0,
            status="FAILED",
            error_message=error_message,
        )

    with engine.begin() as conn:
        # Sempre reprocessa arquivo; sobrescrita ocorre por chave de negocio na silver.
        _registrar_arquivo(conn, file_path.name, file_hash, file_type, "RUNNING", 0, "")

    try:
        if file_type == "movimentacoes_json":
            records = ler_registros_json(file_path)
        else:
            records = ler_registros_csv(file_path)

        with engine.begin() as conn:
            if file_type == "movimentacoes_json":
                loaded = _carregar_movimentacoes(conn, file_path.name, records)
            else:
                loaded = _carregar_produtos(conn, file_path.name, records)

            _registrar_arquivo(conn, file_path.name, file_hash, file_type, "SUCCESS", loaded, "")

        _mover_arquivo(file_path, processed_dir)
        return ResultadoEtl(file_name=file_path.name, file_type=file_type, rows_loaded=loaded, status="SUCCESS")

    except Exception as exc:
        with engine.begin() as conn:
            _registrar_arquivo(conn, file_path.name, file_hash, file_type, "FAILED", 0, str(exc)[:3000])
        _mover_arquivo(file_path, failed_dir)
        return ResultadoEtl(file_name=file_path.name, file_type=file_type, rows_loaded=0, status="FAILED", error_message=str(exc))


# Finalidade: Processa todos os arquivos disponiveis no diretorio de entrada.
def processar_diretorio(
    input_dir: str | Path,
    processed_dir: str | Path,
    failed_dir: str | Path,
    engine: Engine | None = None,
) -> List[ResultadoEtl]:
    """Processa todos os arquivos disponiveis no diretorio de entrada."""
    engine = engine or obter_engine()
    input_path = Path(input_dir)
    processed_path = Path(processed_dir)
    failed_path = Path(failed_dir)

    input_path.mkdir(parents=True, exist_ok=True)
    processed_path.mkdir(parents=True, exist_ok=True)
    failed_path.mkdir(parents=True, exist_ok=True)

    files = sorted([p for p in input_path.iterdir() if p.is_file()])
    results: List[ResultadoEtl] = []

    for file_path in files:
        results.append(processar_arquivo(file_path, engine, processed_path, failed_path))

    return results


# Finalidade: Executa um ciclo unico de ETL.
def executar_uma_vez(
    input_dir: str | Path | None = None,
    processed_dir: str | Path | None = None,
    failed_dir: str | Path | None = None,
) -> List[ResultadoEtl]:
    """Executa um ciclo unico de ETL usando os diretorios configurados."""
    return processar_diretorio(
        input_dir=input_dir or _ler_variavel_ambiente("INPUT_DIR", "./data/pending"),
        processed_dir=processed_dir or _ler_variavel_ambiente("PROCESSED_DIR", "./data/processed"),
        failed_dir=failed_dir or _ler_variavel_ambiente("FAILED_DIR", "./data/failed"),
        engine=obter_engine(),
    )


# Finalidade: Executa ETL continuo com intervalo entre ciclos.
def executar_em_loop(
    sleep_seconds: int = 30,
    input_dir: str | Path | None = None,
    processed_dir: str | Path | None = None,
    failed_dir: str | Path | None = None,
):
    """Executa ETL continuamente, aguardando entre os ciclos."""
    while True:
        results = executar_uma_vez(input_dir=input_dir, processed_dir=processed_dir, failed_dir=failed_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] arquivos avaliados: {len(results)}")
        for result in results:
            print(f"  - {result.file_name}: {result.status} ({result.rows_loaded} linhas)")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    executar_uma_vez()
