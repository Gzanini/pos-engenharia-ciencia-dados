CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS bronze.file_registry (
    id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,
    file_type TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_loaded INTEGER DEFAULT 0,
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS bronze.movimentacoes_raw (
    id BIGSERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    record_hash TEXT NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    ingestion_ts TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bronze.produtos_servicos_raw (
    id BIGSERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    record_hash TEXT NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    ingestion_ts TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS silver.fato_movimentacoes (
    id BIGSERIAL PRIMARY KEY,
    record_hash TEXT NOT NULL UNIQUE,
    source_file TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    data_emissao DATE,
    id_produto_servico TEXT,
    id_produto_servico_empresa TEXT,
    cd_cfop TEXT,
    descricao_cfop TEXT,
    cd_modelo TEXT,
    descricao_modelo TEXT,
    cd_modelo_fiscal TEXT,
    cd_situacao TEXT,
    descricao_situacao TEXT,
    direcao_estoque TEXT,
    tipo_transacao TEXT,
    id_pessoa TEXT,
    status_item_cancelado BOOLEAN,
    qtd_item_movimentacao NUMERIC(18,4),
    qtd_venda NUMERIC(18,4),
    valor_unitario NUMERIC(18,4),
    valor_desconto_digitado NUMERIC(18,4),
    valor_desconto_proporcional NUMERIC(18,4),
    valor_frete_item NUMERIC(18,4),
    valor_total_bruto NUMERIC(18,4),
    valor_total_liquido NUMERIC(18,4),
    ingestion_ts TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fato_mov_data ON silver.fato_movimentacoes (data_emissao);
CREATE INDEX IF NOT EXISTS idx_fato_mov_produto ON silver.fato_movimentacoes (id_produto_servico);

CREATE TABLE IF NOT EXISTS silver.dim_produtos_servicos (
    id BIGSERIAL PRIMARY KEY,
    id_produto_servico TEXT NOT NULL UNIQUE,
    cd_produto_servico TEXT,
    descricao TEXT,
    status_produto_servico TEXT,
    pesavel BOOLEAN,
    vendavel BOOLEAN,
    percentual_cashback NUMERIC(18,4),
    unidade_sigla TEXT,
    tipo_item_descricao TEXT,
    sub_grupo_referencia TEXT,
    codigo_barras TEXT,
    codigo_barras_tributavel TEXT,
    id_produto_servico_empresa_referencia TEXT,
    id_empresa_referencia TEXT,
    id_estoque_referencia TEXT,
    id_preco_referencia TEXT,
    margem_lucro_aplicada_referencia NUMERIC(18,4),
    limite_desconto_referencia NUMERIC(18,4),
    percentual_comissao_referencia NUMERIC(18,4),
    source_file TEXT,
    ingestion_ts TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE VIEW gold.vw_mix_produtos_diario AS
SELECT
    f.data_emissao,
    f.id_produto_servico,
    COALESCE(d.descricao, 'SEM_DESCRICAO') AS descricao_produto,
    COALESCE(d.tipo_item_descricao, 'SEM_CATEGORIA') AS categoria,
    COUNT(*) AS qt_itens,
    SUM(COALESCE(f.qtd_venda, 0)) AS qtd_vendida,
    SUM(COALESCE(f.valor_total_liquido, 0)) AS faturamento_liquido,
    AVG(COALESCE(f.valor_total_liquido, 0)) AS ticket_medio_item
FROM silver.fato_movimentacoes f
LEFT JOIN silver.dim_produtos_servicos d
    ON d.id_produto_servico = f.id_produto_servico
WHERE COALESCE(f.status_item_cancelado, FALSE) = FALSE
GROUP BY 1, 2, 3, 4;
