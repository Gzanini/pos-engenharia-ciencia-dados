# Projeto Pratico - Mix de Produtos (FS)

Entrega da disciplina `2026/1 - Tipos de Dados Avancados e Modelagem para Ciencia de Dados`.

## Objetivo da entrega
Implementar um pipeline ponta a ponta para analisar mix de produtos, usando os arquivos base de movimentacoes e produtos/servicos.

## Escopo implementado
- Ambiente com Docker Compose (`postgres` + `jupyter`).
- ETL com duas opcoes: execucao unica (`run_once`) e execucao em loop (watcher).
- Carga e estruturacao em PostgreSQL com camadas `bronze`, `silver` e `gold`.
- Analise de mix com join de movimentacoes e dimensao de produtos.
- Notebook de ML curto (clusterizacao de produtos).

## Tipos de dados usados
- JSON: `movimentacoes_*.json`
- CSV: `produtos_servicos_*.csv`

## Estrutura da pasta

```text
tipos-dados-avancados-modelagem-ciencia-dados/
  docker-compose.yml
  README.md
  data/
    pending/
    backup/
    processed/
    failed/
  docker/
    jupyter/
      Dockerfile
      requirements.txt
  notebooks/
    00_monitoramento_banco.ipynb
    01A_etl_run_once.ipynb
    01B_etl_watcher_loop.ipynb
    02_analise_mix.ipynb
    03_ml_conclusoes_v2_20260513.ipynb
  scripts/
    load_base_files.ps1
  sql/
    init/
      001_create_schemas_tables.sql
  src/
    etl_core.py
    run_once.py
    run_watcher.py
```

## Como executar
1. Subir o ambiente:
   ```bash
   docker compose up --build -d
   ```
2. Copiar os arquivos base para `data/pending`:
   - Origem: `C:\Users\Guilherme_Zanini\Desktop\Pos-unisinos\tipos_de_dados\Arquivos base`
   - Script pronto: `scripts/load_base_files.ps1`
3. Abrir Jupyter:
   - URL: `http://localhost:8888`
   - Token padrao: `python@2026`
4. Executar notebooks:
   - `notebooks/00_monitoramento_banco.ipynb` (monitoramento)
   - `notebooks/01A_etl_run_once.ipynb` (didatico, com explicacao da logica)
   - `notebooks/02_analise_mix.ipynb`
   - `notebooks/03_ml_conclusoes_v2_20260513.ipynb`
5. Opcional: ingestao continua com watcher:
   - `notebooks/01B_etl_watcher_loop.ipynb` (operacional, reutiliza `src/etl_core.py`)

## Configuracao do .env
Crie um arquivo `.env` na raiz desta pasta com o seguinte conteudo:

```env
POSTGRES_DB=fs_mix
POSTGRES_USER=fs_user
POSTGRES_PASSWORD=fs_pass
POSTGRES_PORT=5432
JUPYTER_PORT=8888
JUPYTER_TOKEN=python@2026
```

## Tabelas principais criadas automaticamente
O script `sql/init/001_create_schemas_tables.sql` roda na inicializacao do Postgres (volume novo) e cria:
- `bronze.file_registry`
- `bronze.movimentacoes_raw`
- `bronze.produtos_servicos_raw`
- `silver.fato_movimentacoes`
- `silver.dim_produtos_servicos`
- `gold.vw_mix_produtos_diario`

## Observacoes
- Use `data/backup` para manter arquivos de origem aguardando; arraste para `data/pending` quando quiser processar.
- Arquivos processados sao movidos para `data/processed`.
- Arquivos com erro sao movidos para `data/failed`.
- O ETL sempre reprocessa arquivos e sobrescreve movimentacoes pela chave de negocio: `id_movimentacao + id_produto_servico + id_pessoa`.
- Para produtos/servicos, a sobrescrita ocorre por `id_produto_servico`.
- O `bronze.file_registry` registra o ultimo processamento por arquivo (status, linhas e horario).

