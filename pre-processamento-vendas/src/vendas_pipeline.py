from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


MOV_NUMERIC_COLUMNS = [
    "valor_desconto_digitado",
    "valor_desconto_proporcional",
    "valor_frete_item",
    "qtd_item_movimentacao",
    "qtd_venda",
    "valor_unitario",
]

PROD_NUMERIC_COLUMNS = [
    "percentual_cashback",
    "margem_lucro_aplicada_referencia",
    "limite_desconto_referencia",
    "percentual_comissao_referencia",
]

PROD_BOOL_COLUMNS = [
    "status_produto_servico",
    "pesavel",
    "vendavel",
    "flag_item_ativo",
]


def resolve_project_root(start_path: Path | None = None) -> Path:
    current_path = (start_path or Path.cwd()).resolve()
    if current_path.name == "notebooks":
        current_path = current_path.parent
    elif not (current_path / "dados").exists() and (current_path.parent / "dados").exists():
        current_path = current_path.parent
    return current_path


def load_movimentacoes(raw_dir: Path) -> pd.DataFrame:
    arquivos = sorted(raw_dir.glob("movimentacoes_*.json"))
    quadros = []
    for arquivo in arquivos:
        with arquivo.open(encoding="utf-8") as handler:
            registros = json.load(handler)
        quadro = pd.DataFrame(registros)
        quadro["_arquivo_origem"] = arquivo.name
        quadros.append(quadro)
    if not quadros:
        raise FileNotFoundError(f"Nenhum arquivo movimentacoes_*.json encontrado em {raw_dir}")
    return pd.concat(quadros, ignore_index=True)


def load_produtos(raw_dir: Path) -> pd.DataFrame:
    arquivo = raw_dir / "produtos_servicos_20260512.csv"
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")
    return pd.read_csv(arquivo)


def cast_types_movimentacoes(df_mov: pd.DataFrame) -> pd.DataFrame:
    df = df_mov.copy()
    for coluna in MOV_NUMERIC_COLUMNS:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    df["data_emissao"] = pd.to_datetime(df["data_emissao"], errors="coerce")
    df["status_item_cancelado"] = df["status_item_cancelado"].astype(str).str.lower().map({"true": True, "false": False})
    return df


def cast_types_produtos(df_prod: pd.DataFrame) -> pd.DataFrame:
    df = df_prod.copy()
    for coluna in PROD_BOOL_COLUMNS:
        df[coluna] = df[coluna].astype(str).str.lower().map({"true": True, "false": False})
    for coluna in PROD_NUMERIC_COLUMNS:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    return df


def merge_base(df_mov: pd.DataFrame, df_prod: pd.DataFrame) -> pd.DataFrame:
    return df_mov.merge(df_prod, on="id_produto_servico", how="left", suffixes=("_mov", "_prod"))


def clean_base(df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()
    for coluna in [
        "descricao",
        "descricao_modelo",
        "descricao_situacao",
        "descricao_cfop",
        "tipo_item_descricao",
        "sub_grupo_referencia",
        "unidade_sigla",
    ]:
        if coluna in df.columns:
            df[coluna] = df[coluna].fillna("desconhecido")

    df = df.drop_duplicates().copy()
    df = df.dropna(subset=["data_emissao", "id_produto_servico", "qtd_venda", "valor_unitario"]).copy()

    df = df[df["tipo_transacao"].astype(str).str.upper().eq("VENDA")].copy()
    df = df[df["direcao_estoque"].astype(str).str.upper().eq("SAIDA")].copy()
    df["status_item_cancelado"] = df["status_item_cancelado"].fillna(False)
    df = df[~df["status_item_cancelado"]].copy()

    df["codigo_barras"] = df["codigo_barras"].fillna("").astype(str).str.strip()
    df["codigo_barras_tributavel"] = df["codigo_barras_tributavel"].fillna("").astype(str).str.strip()
    return df


def engineer_features(df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()
    df["receita_bruta_item"] = df["qtd_venda"] * df["valor_unitario"]
    df["desconto_total_item"] = df[["valor_desconto_digitado", "valor_desconto_proporcional"]].fillna(0).sum(axis=1)
    df["receita_liquida_item"] = df["receita_bruta_item"] - df["desconto_total_item"] + df["valor_frete_item"].fillna(0)
    df["percentual_desconto_item"] = np.where(
        df["receita_bruta_item"] > 0,
        (df["desconto_total_item"] / df["receita_bruta_item"]) * 100,
        0,
    )
    df["tem_desconto"] = df["desconto_total_item"] > 0
    df["quantidade_arredondada"] = df["qtd_venda"].round(0)
    return df


def flag_outliers_receita(df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()
    q1 = df["receita_liquida_item"].quantile(0.25)
    q3 = df["receita_liquida_item"].quantile(0.75)
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr
    df["flag_outlier_receita"] = ~df["receita_liquida_item"].between(limite_inferior, limite_superior)
    return df


def add_time_features(df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()
    mapa_dias = {
        0: "segunda",
        1: "terca",
        2: "quarta",
        3: "quinta",
        4: "sexta",
        5: "sabado",
        6: "domingo",
    }
    df["dia_semana"] = df["data_emissao"].dt.dayofweek.map(mapa_dias)
    df["mes_referencia"] = df["data_emissao"].dt.strftime("%Y-%m")
    df["eh_final_de_semana"] = df["dia_semana"].isin(["sabado", "domingo"])
    df["faixa_receita"] = pd.cut(
        df["receita_liquida_item"],
        bins=[-np.inf, 0, 50, 100, np.inf],
        labels=["sem_receita", "baixa", "media", "alta"],
    )
    return df


def create_model_matrix(df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()
    colunas_categoricas = ["tipo_item_descricao", "unidade_sigla", "dia_semana", "faixa_receita"]
    df = pd.get_dummies(df, columns=colunas_categoricas, drop_first=True)

    colunas_norm = ["qtd_venda", "valor_unitario", "receita_bruta_item", "receita_liquida_item"]
    scaler = StandardScaler()
    df[[f"{col}_z" for col in colunas_norm]] = scaler.fit_transform(df[colunas_norm])
    return df


def build_pipeline(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_mov = cast_types_movimentacoes(load_movimentacoes(raw_dir))
    df_prod = cast_types_produtos(load_produtos(raw_dir))
    df_base = merge_base(df_mov, df_prod)
    df_base = clean_base(df_base)
    df_base = engineer_features(df_base)
    df_base = flag_outliers_receita(df_base)
    df_base = add_time_features(df_base)
    df_model = create_model_matrix(df_base)
    return df_base, df_model


def summarize_sales(df_base: pd.DataFrame) -> dict[str, pd.DataFrame]:
    top_products = (
        df_base.groupby("descricao", as_index=False)["receita_liquida_item"]
        .sum()
        .sort_values("receita_liquida_item", ascending=False)
        .head(10)
    )
    revenue_by_day = (
        df_base.groupby("data_emissao", as_index=False)["receita_liquida_item"]
        .sum()
        .sort_values("data_emissao")
    )
    revenue_by_category = (
        df_base.groupby("tipo_item_descricao", as_index=False)["receita_liquida_item"]
        .sum()
        .sort_values("receita_liquida_item", ascending=False)
    )
    return {
        "top_products": top_products,
        "revenue_by_day": revenue_by_day,
        "revenue_by_category": revenue_by_category,
    }


def save_outputs(df_base: pd.DataFrame, df_model: pd.DataFrame, processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    df_base.to_csv(processed_dir / "base_vendas_tratada.csv", index=False)
    df_model.to_csv(processed_dir / "base_vendas_modelagem.csv", index=False)
