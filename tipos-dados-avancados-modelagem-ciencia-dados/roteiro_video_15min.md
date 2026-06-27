# Roteiro Base - Video de Entrega (ate 15 min)

Disciplina: Tipos de Dados Avancados e Modelagem para Ciencia de Dados
Projeto: Mix de Produtos (FS) com ETL + Analise + ML

## Duracao sugerida: 12 a 15 minutos

## 0) Abertura (1 min)
- Apresentar problema: entender mix de produtos para apoiar decisao de negocio.
- Explicar tipos de dados usados:
  - JSON de movimentacoes
  - CSV de produtos/servicos
- Dizer que o pipeline foi implementado com Docker Compose, PostgreSQL e Jupyter.

## 1) Ambiente e arquitetura (1.5 min)
Notebook de apoio: `README.md` e `docker-compose.yml`
- Mostrar servicos: `postgres` e `jupyter`.
- Mostrar pastas operacionais:
  - `data/pending` (entrada)
  - `data/processed` (sucesso)
  - `data/failed` (erro)
  - `data/backup` (estoque para novos testes)
- Explicar camadas:
  - `bronze` (raw)
  - `silver` (tratado)
  - `gold` (view analitica)

## 2) ETL didatico (3 min)
Notebook: `notebooks/01A_etl_run_once.ipynb`
- Explicar logica passo a passo:
  1. detectar tipo do arquivo
  2. parsear registros
  3. gravar raw em bronze
  4. transformar para silver
  5. registrar processamento em `bronze.file_registry`
- Destacar regra de reprocessamento:
  - ao rodar de novo, o ETL faz sobrescrita por chave de negocio em movimentacoes (`id_movimentacao + id_produto_servico + id_pessoa`) e por `id_produto_servico` em produtos.
- Executar uma carga rapida e mostrar contagens finais.

## 3) ETL continuo (1.5 min)
Notebook: `notebooks/01B_etl_watcher_loop.ipynb`
- Explicar que o 1B e a evolucao operacional do 1A.
- Mostrar que o 1B usa `src/etl_core.py` para loop recorrente.
- Falar quando usar:
  - 1A para aula/apresentacao didatica
  - 1B para operacao continua

## 4) Analise de mix e visualizacao (3 min)
Notebook: `notebooks/02_analise_mix.ipynb`
- Mostrar join entre `silver.fato_movimentacoes` e `silver.dim_produtos_servicos`.
- Exibir:
  - top categorias por faturamento
  - top produtos
  - curva ABC / concentracao de faturamento
- Trazer 2 ou 3 insights de negocio objetivos.

## 5) Machine Learning (2 min)
Notebook: `notebooks/03_ml_conclusoes_v2_20260513.ipynb`
- Explicar tecnica aplicada (KMeans para cluster de produtos).
- Mostrar grafico de clusters e interpretacao.
- Exemplo de leitura:
  - cluster premium com maior ticket medio por produto
  - cluster com maior recorrencia de venda (mais dias com venda)
  - cluster de cauda longa com menor faturamento medio

## 6) Monitoramento e rastreabilidade (1 min)
Notebook: `notebooks/00_monitoramento_banco.ipynb`
- Mostrar consultas prontas:
  - status da carga em `file_registry`
  - contagens de tabelas
  - amostras de dados
- Reforcar confiabilidade do pipeline para reproducao.

## 7) Fechamento (1 min)
- Confirmar aderencia ao enunciado:
  - 2 tipos de dados
  - Docker Compose
  - pipeline completo
  - tecnica de ML
  - documentacao em notebooks
- Limites atuais:
  - modelo simples (KMeans basico)
  - oportunidades de evolucao (features e validacao de modelo)
- Encerrar com principais aprendizados.

---

## Checklist antes de gravar
- `docker compose up -d` com servicos healthy.
- Ter arquivos em `data/pending` para demonstrar ETL.
- Rodar notebooks na ordem:
  1. `00_monitoramento_banco.ipynb`
  2. `01A_etl_run_once.ipynb`
  3. `02_analise_mix.ipynb`
  4. `03_ml_conclusoes_v2_20260513.ipynb`
- Deixar `01B` como demonstracao complementar de automacao.

