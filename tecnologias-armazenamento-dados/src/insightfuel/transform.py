from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import pstdev


REQUIRED_COLUMNS = {
    "cnpj_revenda",
    "estabelecimento",
    "uf",
    "municipio",
    "produto",
    "data_coleta",
    "valor_venda",
    "bandeira",
}

COLUMN_ALIASES = {
    "cnpj_da_revenda": "cnpj_revenda",
    "razao_social": "estabelecimento",
    "revenda": "estabelecimento",
    "estado_sigla": "uf",
    "municipio": "municipio",
    "produto": "produto",
    "data_da_coleta": "data_coleta",
    "valor_de_venda": "valor_venda",
    "bandeira": "bandeira",
}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"['’]", "", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().upper()


def _canonical_header(value: str) -> str:
    normalized = normalize_name(value)
    return COLUMN_ALIASES.get(normalized, normalized)


def _parse_decimal(value: str) -> Decimal:
    value = value.strip().replace(" ", "")
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    return Decimal(value)


def read_and_clean_csv(content: bytes) -> list[dict[str, object]]:
    text = content.decode("utf-8-sig")
    sample = text[:4096]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("O arquivo CSV está vazio ou não possui cabeçalho")

    mapped_headers = {_canonical_header(name): name for name in reader.fieldnames}
    missing = sorted(REQUIRED_COLUMNS - set(mapped_headers))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(missing)}")

    cleaned: list[dict[str, object]] = []
    seen_rows: set[tuple[object, ...]] = set()
    observation_keys: set[tuple[str, str, str, float]] = set()
    for line_number, raw in enumerate(reader, start=2):
        row = {canonical: (raw[source] or "").strip() for canonical, source in mapped_headers.items()}
        if not any(row.values()):
            continue
        empty = sorted(column for column in REQUIRED_COLUMNS if not str(row[column]).strip())
        if empty:
            raise ValueError(
                f"Colunas obrigatórias sem valor na linha {line_number}: {', '.join(empty)}"
            )
        try:
            date_value = datetime.strptime(str(row["data_coleta"]), "%d/%m/%Y").date().isoformat()
        except ValueError as exc:
            raise ValueError(f"Data inválida na linha {line_number}: {row['data_coleta']}") from exc
        try:
            price = _parse_decimal(str(row["valor_venda"]))
        except InvalidOperation as exc:
            raise ValueError(f"Valor de venda inválido na linha {line_number}: {row['valor_venda']}") from exc
        if price <= 0:
            raise ValueError(f"Valor de venda deve ser positivo na linha {line_number}")

        normalized = {
            "cnpj_revenda": re.sub(r"\D", "", str(row["cnpj_revenda"])),
            "estabelecimento": str(row["estabelecimento"]).upper(),
            "uf": str(row["uf"]).upper(),
            "municipio": normalize_text(str(row["municipio"])),
            "produto": str(row["produto"]).upper(),
            "data_coleta": date_value,
            "valor_venda": float(price),
            "bandeira": str(row["bandeira"]).upper(),
        }
        if not normalized["cnpj_revenda"] or not normalized["produto"]:
            raise ValueError(f"Chave de negócio incompleta na linha {line_number}")
        row_tuple = tuple(normalized[column] for column in sorted(REQUIRED_COLUMNS))
        if row_tuple in seen_rows:
            continue
        seen_rows.add(row_tuple)
        key = (
            str(normalized["cnpj_revenda"]),
            str(normalized["produto"]),
            str(normalized["data_coleta"]),
            float(normalized["valor_venda"]),
        )
        if key in observation_keys:
            raise ValueError(
                "Observação ANP duplicada com atributos divergentes: "
                + " | ".join(str(value) for value in key)
            )
        observation_keys.add(key)
        cleaned.append(normalized)

    if not cleaned:
        raise ValueError("O arquivo não contém registros válidos")
    return cleaned


def read_and_clean_csv_files(files: list[tuple[str, bytes]]) -> list[dict[str, object]]:
    if not files:
        raise ValueError("Nenhum arquivo CSV foi encontrado na Bronze")

    rows_by_key: dict[tuple[str, str, str, float], dict[str, object]] = {}
    for filename, content in files:
        for row in read_and_clean_csv(content):
            key = (
                str(row["cnpj_revenda"]),
                str(row["produto"]),
                str(row["data_coleta"]),
                float(row["valor_venda"]),
            )
            previous = rows_by_key.get(key)
            if previous is not None and previous != row:
                raise ValueError(
                    "Chave de negócio conflitante entre arquivos da Bronze: "
                    f"{' | '.join(str(value) for value in key)} (arquivo {filename})"
                )
            rows_by_key[key] = row
    return list(rows_by_key.values())


SOURCE_ALIASES = {
    "populacao": {
        "codigo_do_municipio": "codigo_municipio",
        "cod_municipio": "codigo_municipio",
        "nome_do_municipio": "municipio",
        "sigla_da_unidade_da_federacao": "uf",
        "populacao_estimada": "populacao",
    },
    "pib": {
        "codigo_do_municipio": "codigo_municipio",
        "cod_municipio": "codigo_municipio",
        "nome_do_municipio": "municipio",
        "sigla_da_unidade_da_federacao": "uf",
        "produto_interno_bruto_a_precos_correntes_r_1_000": "pib",
        "produto_interno_bruto_per_capita_a_precos_correntes_r_1_00": "pib_per_capita",
    },
    "ipca": {
        "numero_indice": "numero_indice",
        "indice": "numero_indice",
        "variacao": "variacao_percentual",
        "variacao_percentual": "variacao_percentual",
    },
}

SOURCE_REQUIRED = {
    "populacao": {"codigo_municipio", "municipio", "uf", "ano", "populacao"},
    "pib": {"codigo_municipio", "municipio", "uf", "ano", "pib", "pib_per_capita"},
    "ipca": {"ano", "mes", "numero_indice", "variacao_percentual"},
}

SOURCE_KEYS = {
    "populacao": ("codigo_municipio", "ano"),
    "pib": ("codigo_municipio", "ano"),
    "ipca": ("ano", "mes"),
}

MONTHS_PT = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}


def _spreadsheet_module():
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("Instale pandas, openpyxl e xlrd para processar planilhas IBGE") from exc
    return pd


def _read_population_spreadsheet(filename: str, content: bytes) -> list[dict[str, object]]:
    pd = _spreadsheet_module()
    base_name = Path(filename).name
    year_match = re.search(r"(20\d{2})", base_name)
    if not year_match:
        raise ValueError(f"Ano não identificado no arquivo de população: {base_name}")
    year = int(year_match.group(1))
    book = pd.ExcelFile(io.BytesIO(content))
    sheet = next((name for name in book.sheet_names if "municip" in normalize_name(name)), None)
    if sheet is None:
        raise ValueError(f"Aba de municípios não encontrada em {filename}")
    frame = pd.read_excel(io.BytesIO(content), sheet_name=sheet, header=1, dtype=str)
    columns = {normalize_name(name): name for name in frame.columns}
    required = {"uf", "cod_uf", "cod_munic", "nome_do_municipio", "populacao_estimada"}
    missing = sorted(required - set(columns))
    if missing:
        raise ValueError(f"Layout oficial de população inválido em {filename}: {', '.join(missing)}")
    rows = []
    for _, raw in frame.iterrows():
        uf = str(raw[columns["uf"]]).strip().upper()
        uf_code = re.sub(r"\D", "", str(raw[columns["cod_uf"]])).zfill(2)
        municipal_code = re.sub(r"\D", "", str(raw[columns["cod_munic"]])).zfill(5)
        municipality = str(raw[columns["nome_do_municipio"]]).strip().upper()
        population_text = re.sub(r"[^0-9]", "", str(raw[columns["populacao_estimada"]]))
        if not re.fullmatch(r"[A-Z]{2}", uf):
            continue
        if not population_text or not municipality:
            raise ValueError(f"Registro municipal incompleto em {filename}")
        rows.append({
            "codigo_municipio": uf_code + municipal_code,
            "municipio": normalize_text(municipality),
            "uf": uf,
            "ano": year,
            "populacao": int(population_text),
        })
    if not rows:
        raise ValueError(f"Nenhum município encontrado em {filename}")
    return rows


def _read_pib_spreadsheet(filename: str, content: bytes) -> list[dict[str, object]]:
    pd = _spreadsheet_module()
    frame = pd.read_excel(io.BytesIO(content), sheet_name="PIB dos Municípios")
    columns = {normalize_name(name): name for name in frame.columns}
    aliases = SOURCE_ALIASES["pib"]
    canonical = {aliases.get(name, name): original for name, original in columns.items()}
    missing = sorted(SOURCE_REQUIRED["pib"] - set(canonical))
    if missing:
        raise ValueError(f"Layout oficial do PIB inválido em {filename}: {', '.join(missing)}")
    selected = frame[[canonical[name] for name in SOURCE_REQUIRED["pib"]]].copy()
    selected.columns = list(SOURCE_REQUIRED["pib"])
    rows = []
    for raw in selected.to_dict(orient="records"):
        rows.append({
            "codigo_municipio": re.sub(r"\D", "", str(raw["codigo_municipio"])),
            "municipio": normalize_text(str(raw["municipio"])),
            "uf": str(raw["uf"]).strip().upper(),
            "ano": int(raw["ano"]),
            "pib": float(raw["pib"]),
            "pib_per_capita": float(raw["pib_per_capita"]),
        })
    return rows


def _read_ipca_spreadsheet(filename: str, content: bytes) -> list[dict[str, object]]:
    pd = _spreadsheet_module()
    frame = pd.read_excel(io.BytesIO(content), sheet_name=0, header=None)
    rows = []
    current_year = None
    for values in frame.itertuples(index=False, name=None):
        first = values[0]
        if pd.notna(first):
            try:
                candidate = int(float(first))
                if 1900 <= candidate <= 2100:
                    current_year = candidate
            except (TypeError, ValueError):
                pass
        month = MONTHS_PT.get(str(values[1]).strip().upper()) if len(values) > 1 else None
        if current_year is None or month is None:
            continue
        try:
            index_number = float(values[2])
            monthly_change = float(values[3])
        except (TypeError, ValueError):
            continue
        rows.append({
            "ano": current_year,
            "mes": month,
            "numero_indice": index_number,
            "variacao_percentual": monthly_change,
        })
    if not rows:
        raise ValueError(f"Nenhuma observação IPCA encontrada em {filename}")
    return rows


def _read_official_spreadsheet(source: str, filename: str, content: bytes) -> list[dict[str, object]]:
    if source == "populacao":
        return _read_population_spreadsheet(filename, content)
    if source == "pib":
        return _read_pib_spreadsheet(filename, content)
    if source == "ipca":
        return _read_ipca_spreadsheet(filename, content)
    raise ValueError(f"Planilha não suportada para {source}: {filename}")


def _read_generic_source_csv(source: str, content: bytes) -> list[dict[str, object]]:
    text = content.decode("utf-8-sig")
    delimiter = ";" if text[:4096].count(";") > text[:4096].count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError(f"Arquivo {source} vazio ou sem cabeçalho")

    aliases = SOURCE_ALIASES[source]
    mapped = {
        aliases.get(normalize_name(name), normalize_name(name)): name
        for name in reader.fieldnames
    }
    missing = sorted(SOURCE_REQUIRED[source] - set(mapped))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes em {source}: {', '.join(missing)}")

    rows = []
    seen: set[tuple[object, ...]] = set()
    for line_number, raw in enumerate(reader, start=2):
        row = {canonical: (raw[original] or "").strip() for canonical, original in mapped.items()}
        if not any(row.values()):
            continue
        empty = sorted(column for column in SOURCE_REQUIRED[source] if not row[column])
        if empty:
            raise ValueError(
                f"Campos obrigatórios vazios em {source}, linha {line_number}: {', '.join(empty)}"
            )
        try:
            if source == "populacao":
                cleaned = {
                    "codigo_municipio": re.sub(r"\D", "", row["codigo_municipio"]),
                    "municipio": normalize_text(row["municipio"]),
                    "uf": row["uf"].upper(),
                    "ano": int(row["ano"]),
                    "populacao": int(_parse_decimal(row["populacao"])),
                }
            elif source == "pib":
                cleaned = {
                    "codigo_municipio": re.sub(r"\D", "", row["codigo_municipio"]),
                    "municipio": normalize_text(row["municipio"]),
                    "uf": row["uf"].upper(),
                    "ano": int(row["ano"]),
                    "pib": float(_parse_decimal(row["pib"])),
                    "pib_per_capita": float(_parse_decimal(row["pib_per_capita"])),
                }
            else:
                cleaned = {
                    "ano": int(row["ano"]),
                    "mes": int(row["mes"]),
                    "numero_indice": float(_parse_decimal(row["numero_indice"])),
                    "variacao_percentual": float(_parse_decimal(row["variacao_percentual"])),
                }
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Valor inválido em {source}, linha {line_number}") from exc

        if source in {"populacao", "pib"} and not cleaned["codigo_municipio"]:
            raise ValueError(f"Código de município inválido em {source}, linha {line_number}")
        if source == "populacao" and cleaned["populacao"] <= 0:
            raise ValueError(f"População não positiva na linha {line_number}")
        if source == "ipca" and not 1 <= cleaned["mes"] <= 12:
            raise ValueError(f"Mês inválido em IPCA, linha {line_number}")

        signature = tuple(cleaned[column] for column in sorted(cleaned))
        if signature not in seen:
            seen.add(signature)
            rows.append(cleaned)
    if not rows:
        raise ValueError(f"Arquivo {source} não contém registros válidos")
    return rows


def read_and_clean_source_files(
    source: str, files: list[tuple[str, bytes]]
) -> list[dict[str, object]]:
    if source == "anp":
        return read_and_clean_csv_files(files)
    if source not in SOURCE_REQUIRED:
        raise ValueError(f"Fonte desconhecida: {source}")
    if not files:
        raise ValueError(f"Nenhum arquivo encontrado para {source}")

    rows_by_key: dict[tuple[object, ...], dict[str, object]] = {}
    key_columns = SOURCE_KEYS[source]
    for filename, content in files:
        if Path(filename).suffix.lower() in {".xls", ".xlsx"}:
            source_rows = _read_official_spreadsheet(source, filename, content)
        else:
            source_rows = _read_generic_source_csv(source, content)
        for row in source_rows:
            key = tuple(row[column] for column in key_columns)
            previous = rows_by_key.get(key)
            if previous is not None and previous != row:
                raise ValueError(f"Chave conflitante em {source}: {key} (arquivo {filename})")
            rows_by_key[key] = row
    return list(rows_by_key.values())


def aggregate_monthly(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        month = str(row["data_coleta"])[:7]
        groups[(str(row["uf"]), str(row["municipio"]), str(row["produto"]), month)].append(
            float(row["valor_venda"])
        )

    result = []
    for (uf, city, product, month), prices in sorted(groups.items()):
        year, month_number = month.split("-")
        result.append(
            {
                "ano": int(year),
                "mes": int(month_number),
                "uf": uf,
                "municipio": city,
                "produto": product,
                "preco_medio": sum(prices) / len(prices),
                "preco_minimo": min(prices),
                "preco_maximo": max(prices),
                "desvio_padrao_preco": pstdev(prices),
                "quantidade_observacoes": len(prices),
            }
        )
    return result

