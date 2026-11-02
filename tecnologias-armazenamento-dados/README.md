# InsightFuel - Pipeline de Dados com Airflow, GCS e BigQuery

Entrega da disciplina `2026/2 - Tecnologias de Armazenamento de Dados para Ciencia de Dados`.

## Objetivo da entrega

Implementar um pipeline funcional e reprodutivel para integrar precos de combustiveis da ANP com dados de populacao, PIB municipal e IPCA do IBGE.

O projeto recebe arquivos de uma pasta local, valida os layouts, preserva os dados brutos no Google Cloud Storage, cria tabelas tratadas no BigQuery e disponibiliza uma camada Gold pronta para consumo analitico.

## Escopo implementado

- Apache Airflow 2.10.5 executado localmente com Docker Compose.
- PostgreSQL para os metadados do Airflow.
- Conexao direta com um projeto Google Cloud por Application Default Credentials.
- Quatro fontes: ANP, populacao, PIB municipal e IPCA.
- Arquitetura Medallion com Bronze, Silver e Gold.
- Validacao de layout antes do envio para a Bronze.
- Historico de arquivos validos e rejeitados por `run_id` no GCS.
- Quatro tabelas Silver e uma tabela Gold no BigQuery.
- Controle de ingestao append-only no BigQuery.
- Validacoes bloqueantes de campos obrigatorios e integridade da Gold.
- Reprocessamento idempotente das tabelas analiticas.
- Oito testes automatizados.
- Evidencias da execucao real no Airflow, GCS e BigQuery.

## Arquitetura

```text
Arquivos locais
  data/input/<fonte>/
          |
          v
Apache Airflow em Docker
  validar layout -> GCS/Bronze -> BigQuery/Silver
                                        |
                                        v
                                  validar Silver
                                        |
                                        v
                              agregar e integrar Gold
                                        |
                                        v
                                   validar Gold
                                        |
                                        v
                               arquivar Bronze no GCS
```

Para cada fonte existem tres tasks: `validar_layout`, `ingestao_bronze` e `processar_silver`. Depois das quatro branches, a DAG executa `validar_silver`, `gerar_gold`, `validar_gold` e `arquivar_bronze`, totalizando 16 tasks.

## Fontes de dados

| Fonte | Instituicao | Formatos aceitos | Granularidade |
|---|---|---|---|
| Precos de combustiveis | ANP | CSV | posto, produto e data |
| Estimativas da populacao | IBGE | CSV, XLS e XLSX | municipio e ano |
| PIB dos Municipios | IBGE | CSV e XLSX | municipio e ano |
| IPCA | IBGE | CSV, XLS e XLSX | ano e mes |

Paginas oficiais:

- [ANP - Serie Historica de Precos de Combustiveis e GLP](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis)
- [IBGE - Estimativas da Populacao](https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-population.html)
- [IBGE - PIB dos Municipios](https://www.ibge.gov.br/estatisticas/economicas/contas-nacionais/9088-produtointerno-bruto-dos-municipios.html)
- [IBGE - IPCA](https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html)

## Resultado da execucao completa

A execucao `real_full_20260930_0140` processou dez arquivos oficiais e concluiu as 16 tasks com sucesso.

| Resultado | Registros | Cobertura |
|---|---:|---|
| Silver ANP | 2.125.555 | 2024-01-01 a 2026-06-30 |
| Silver populacao | 16.712 | 2024 a 2026 |
| Silver PIB | 77.965 | 2010 a 2023 |
| Silver IPCA | 392 | 1994-01 a 2026-08 |
| Gold integrada | 62.071 | 2024 a 2026 |

Na auditoria final:

- nenhum campo obrigatorio ficou vazio nas quatro tabelas Silver;
- nenhuma linha da Gold ficou sem municipio, populacao, PIB ou IPCA;
- nenhuma agregacao apresentou incoerencia entre preco minimo, medio e maximo;
- dez arquivos validos foram movidos para `archive`;
- nenhum arquivo da execucao permaneceu em `incoming`.

## Principais entregaveis

- `dags/insightfuel_pipeline.py`
  - definicao da DAG, TaskGroups e dependencias;
- `src/insightfuel/`
  - configuracao, transformacoes, GCS, BigQuery e controle;
- `tests/test_pipeline.py`
  - testes automatizados dos contratos e da idempotencia;
- `docker-compose.yml` e `Dockerfile`
  - ambiente local do Airflow;
- `data/samples/`
  - amostras pequenas das quatro fontes;
- `docs/documentacao-completa.md`
  - documentacao tecnica detalhada;
- `docs/guia-entrega-3.md`
  - resumo da DAG e conferencia com a atividade;
- `docs/evidencias/`
  - capturas do Airflow, GCS e BigQuery;
- `docs/referencias/`
  - mapeamento de fontes, desenho de arquitetura e enunciado da Entrega 3.

## Estrutura da pasta

```text
tecnologias-armazenamento-dados/
  .env.example
  airflow_variables.example.json
  docker-compose.yml
  Dockerfile
  pyproject.toml
  README.md
  dags/
    insightfuel_pipeline.py
  data/
    input/
      anp/
      populacao/
      pib/
      ipca/
    samples/
      anp/
      populacao/
      pib/
      ipca/
  docs/
    README.md
    documentacao-completa.md
    guia-entrega-3.md
    evidencias/
    referencias/
  logs/
  scripts/
    load_samples.ps1
    start_airflow.ps1
    trigger_pipeline.ps1
    stop_airflow.ps1
  src/
    insightfuel/
  tests/
    test_pipeline.py
```

## Pre-requisitos

- Docker Desktop;
- PowerShell;
- Google Cloud CLI;
- acesso a um projeto GCP com GCS e BigQuery;
- Application Default Credentials configuradas.

Para autenticar localmente:

```powershell
gcloud auth application-default login
```

## Configuracao

Crie o arquivo `.env` a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

Preencha principalmente:

```env
GCP_PROJECT_ID=seu-projeto-gcp
GCS_BUCKET=seu-bucket-bronze
GCP_LOCATION=southamerica-east1
GCP_ADC_PATH=C:/Users/seu_usuario/AppData/Roaming/gcloud/application_default_credentials.json
```

O `.env` real e a credencial Google nao devem ser versionados.

## Preparacao dos dados

Os dados oficiais completos nao estao no Git devido ao volume. Para uma demonstracao local, copie as amostras para as pastas de entrada:

```powershell
.\scripts\load_samples.ps1
```

Para executar com os arquivos oficiais, coloque-os manualmente em:

```text
data/input/anp/
data/input/populacao/
data/input/pib/
data/input/ipca/
```

Arquivos ZIP devem ser extraidos antes da execucao.

## Como executar

1. Inicialize o ambiente:

   ```powershell
   .\scripts\start_airflow.ps1
   ```

2. Abra o Airflow:

   - URL: `http://localhost:8081`
   - usuario e senha: valores definidos no `.env`.

3. Dispare a DAG:

   ```powershell
   .\scripts\trigger_pipeline.ps1
   ```

4. Acompanhe a DAG `insightfuel_pipeline` na visualizacao Graph ou Grid.

5. Para encerrar:

   ```powershell
   .\scripts\stop_airflow.ps1
   ```

## Testes

Execute os testes dentro da imagem do projeto:

```powershell
docker compose run --rm -T `
  -v "${PWD}/tests:/opt/airflow/project/tests:ro" `
  airflow-webserver `
  python -m unittest discover -s /opt/airflow/project/tests -v
```

Resultado validado: oito testes aprovados.

Para conferir erros de importacao da DAG:

```powershell
docker compose exec -T airflow-webserver `
  airflow dags list-import-errors --output json
```

Resultado esperado: `[]`.

## Documentacao e evidencias

- [Documentacao tecnica completa](docs/documentacao-completa.md)
- [Guia da Entrega 3](docs/guia-entrega-3.md)
- [Indice de documentos e evidencias](docs/README.md)
- [Captura da DAG no Airflow](docs/evidencias/dag-airflow.png)
- [Captura da Bronze no GCS](docs/evidencias/gcs-bronze.png)
- [Captura da tabela Gold](docs/evidencias/bigquery-gold-precos-combustiveis.png)

## Observacoes

- A DAG opera diretamente na GCP; nao ha modo simulado na implementacao entregue.
- Silver e Gold usam `WRITE_TRUNCATE`, evitando duplicacao em reprocessamentos.
- A Bronze preserva o historico por `run_id` em `incoming`, `archive` e `rejected`.
- O controle de ingestao e append-only e registra cada tentativa.
- O Power BI foi mantido fora desta entrega; a Gold esta pronta para conexao futura.
- Nao ha credenciais, `.env`, logs de execucao ou dados oficiais volumosos versionados.

