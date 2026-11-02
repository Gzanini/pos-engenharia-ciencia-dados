# InsightFuel — documentação técnica completa do projeto

> Implementação da Entrega 3 da disciplina **Tecnologias de Armazenamento de Dados para Ciência de Dados**.  
> Estado documentado: **30 de setembro de 2026**.  
> Pipeline validado com os arquivos oficiais disponíveis e execução integral concluída com sucesso.

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Objetivos e escopo](#2-objetivos-e-escopo)
3. [Conformidade com as entregas acadêmicas](#3-conformidade-com-as-entregas-acadêmicas)
4. [Arquitetura implementada](#4-arquitetura-implementada)
5. [Ambiente GCP](#5-ambiente-gcp)
6. [Fontes de dados](#6-fontes-de-dados)
7. [Estrutura do projeto](#7-estrutura-do-projeto)
8. [Ambiente Docker e Airflow](#8-ambiente-docker-e-airflow)
9. [Configuração e Airflow Variables](#9-configuração-e-airflow-variables)
10. [DAG e suas 16 tasks](#10-dag-e-suas-16-tasks)
11. [Processamento detalhado por etapa](#11-processamento-detalhado-por-etapa)
12. [Contratos, schemas e regras por fonte](#12-contratos-schemas-e-regras-por-fonte)
13. [Camada Bronze no GCS](#13-camada-bronze-no-gcs)
14. [Camada Silver no BigQuery](#14-camada-silver-no-bigquery)
15. [Camada Gold no BigQuery](#15-camada-gold-no-bigquery)
16. [Controle de ingestão](#16-controle-de-ingestão)
17. [Qualidade, idempotência e tratamento de falhas](#17-qualidade-idempotência-e-tratamento-de-falhas)
18. [Execução real e resultados](#18-execução-real-e-resultados)
19. [Testes automatizados](#19-testes-automatizados)
20. [Manual de operação](#20-manual-de-operação)
21. [Consultas de auditoria](#21-consultas-de-auditoria)
22. [Segurança e credenciais](#22-segurança-e-credenciais)
23. [Limitações conhecidas e evolução](#23-limitações-conhecidas-e-evolução)
24. [Troubleshooting](#24-troubleshooting)
25. [Links úteis](#25-links-úteis)
26. [Glossário](#26-glossário)

---

## 1. Visão geral

O InsightFuel é um pipeline de dados que combina preços de combustíveis da ANP com três fontes do IBGE:

- estimativas anuais de população municipal;
- Produto Interno Bruto dos Municípios e PIB per capita;
- Índice Nacional de Preços ao Consumidor Amplo — IPCA.

A solução usa uma arquitetura **Medallion**, organizada nas camadas Bronze, Silver e Gold:

- **Bronze:** arquivos brutos preservados no Google Cloud Storage;
- **Silver:** dados tipados, padronizados, deduplicados e separados por fonte no BigQuery;
- **Gold:** preços mensais agregados e integrados a população, PIB, PIB per capita e IPCA;
- **Controle:** eventos append-only de ingestão, validação, carga, rejeição e arquivamento.

O Apache Airflow é executado localmente em Docker e se conecta diretamente ao projeto GCP. Não existe um modo `mock` na DAG entregue. Dependências falsas são usadas somente nos testes unitários isolados.

### Resultado final resumido

| Item | Resultado |
|---|---:|
| Tasks na DAG | 16 |
| Arquivos oficiais processados | 10 |
| Silver ANP | 2.125.555 registros |
| Silver população | 16.712 registros |
| Silver PIB | 77.965 registros |
| Silver IPCA | 392 registros |
| Gold integrada | 62.071 registros |
| Campos obrigatórios inválidos nas Silvers | 0 |
| Integrações ausentes na Gold | 0 |
| Arquivos da execução ainda em `incoming` | 0 |
| Arquivos válidos em `archive` | 10 |
| Testes automatizados | 8 aprovados |
| Erros de importação no Airflow | 0 |

---

## 2. Objetivos e escopo

### 2.1 Objetivo funcional

Receber arquivos de uma pasta local do computador, validar seu layout, enviá-los ao GCS, transformar os dados, carregar as tabelas intermediárias no BigQuery, gerar uma visão analítica integrada e manter rastreabilidade de toda a execução.

### 2.2 Incluído nesta entrega

- Airflow local em Docker;
- conexão real com GCP por Application Default Credentials;
- quatro ingestões paralelas: ANP, população, PIB e IPCA;
- validação antes da Bronze;
- histórico por `run_id` no GCS;
- diretório de rejeitados no GCS;
- quatro tabelas Silver;
- uma tabela Gold integrada;
- tabela de controle de ingestão;
- regras bloqueantes de qualidade;
- idempotência das tabelas analíticas;
- scripts PowerShell de inicialização, disparo e parada;
- testes automatizados;
- amostras pequenas sem credenciais.

### 2.3 Fora do escopo atual

- relatório no Power BI;
- download automático diretamente dos portais ANP/IBGE;
- agendamento periódico da DAG;
- infraestrutura como código para criar o projeto GCP;
- processamento distribuído para volumes muito maiores;
- versionamento histórico dentro das tabelas Silver e Gold.

O Power BI foi deliberadamente adiado. A tabela Gold já está pronta para ser usada como fonte na próxima etapa.

---

## 3. Conformidade com as entregas acadêmicas

### 3.1 Requisitos do professor

O enunciado da Entrega 3 solicita um pipeline funcional com pelo menos três etapas encadeadas no Apache Airflow, sugerindo ingestão, transformação e agregação. Testes básicos de qualidade e proteção contra duplicação são recomendados.

| Requisito | Implementação | Situação |
|---|---|---|
| Pipeline funcional | DAG executada no Airflow local e GCP real | atendido |
| Apache Airflow | Airflow 2.10.5 em Docker | atendido |
| Três ou mais etapas | validação, Bronze, Silver, qualidade, Gold e archive | superado |
| Transformação/limpeza | tipagem, normalização e deduplicação | atendido |
| Agregação/resultado | Gold mensal integrada | atendido |
| Qualidade | validações antes da Bronze, nas Silvers e na Gold | atendido |
| Reprocessamento sem duplicação | `WRITE_TRUNCATE` nas tabelas analíticas | atendido |

### 3.2 Correspondência com o desenho de arquitetura

O desenho acadêmico descreveu 12 tarefas conceituais. A DAG possui 16 tasks porque adiciona validação de layout por fonte e uma etapa explícita de arquivamento.

| Tarefa conceitual | Implementação na DAG |
|---|---|
| 1. Ingestão ANP | `anp.validar_layout` + `anp.ingestao_bronze` |
| 2. Ingestão população | `populacao.validar_layout` + `populacao.ingestao_bronze` |
| 3. Ingestão PIB | `pib.validar_layout` + `pib.ingestao_bronze` |
| 4. Ingestão IPCA | `ipca.validar_layout` + `ipca.ingestao_bronze` |
| 5. Processamento ANP | `anp.processar_silver` |
| 6. Processamento população | `populacao.processar_silver` |
| 7. Processamento PIB | `pib.processar_silver` |
| 8. Processamento IPCA | `ipca.processar_silver` |
| 9. Validação Silver | `validar_silver` |
| 10. Agregação de preços | primeira parte de `gerar_gold` |
| 11. Integração das fontes | segunda parte de `gerar_gold` |
| 12. Disponibilização | tabela Gold + `validar_gold` |
| Controle adicional | tabela `ingestion_events` |
| Histórico adicional | `arquivar_bronze` |

### 3.3 Refinamento da chave ANP

O desenho inicial considerava `CNPJ + produto + data` como chave. Nos arquivos oficiais foram encontradas quatro combinações válidas em que o mesmo posto, produto e data possuíam dois preços diferentes. Para não eliminar observações reais, a implementação usa:

```text
CNPJ + produto + data da coleta + preço observado
```

Duplicatas integrais continuam sendo removidas. O ajuste preserva dados reais e é uma evolução justificada do desenho original.

---

## 4. Arquitetura implementada

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Computador local                                                        │
│                                                                          │
│ data/input/<fonte>                                                       │
│       │                                                                  │
│       ▼                                                                  │
│ Docker Compose                                                           │
│ ├── PostgreSQL 16: metadados do Airflow                                  │
│ ├── Airflow Webserver 2.10.5: interface em localhost:8081                │
│ └── Airflow Scheduler 2.10.5: execução das tasks                         │
│       │                                                                  │
│       └── Application Default Credentials montadas somente para leitura  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ APIs Google Cloud
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Projeto GCP: insightfuel-gzanini-2026                                    │
│                                                                          │
│ GCS — bucket insightfuel-gzanini-2026-bronze                             │
│ └── bronze/<fonte>/{incoming,archive,rejected}/<run_id>/                 │
│                                                                          │
│ BigQuery                                                                 │
│ ├── insightfuel_control.ingestion_events                                 │
│ ├── insightfuel_silver.silver_precos_anp                                 │
│ ├── insightfuel_silver.silver_populacao_ibge                             │
│ ├── insightfuel_silver.silver_pib_municipios_ibge                        │
│ ├── insightfuel_silver.silver_ipca_ibge                                  │
│ └── insightfuel_gold.gold_precos_combustiveis_mensal                     │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                                ▼
                       Power BI — próxima etapa
```

### 4.1 Fluxo lógico

```text
ANP ----------- validar layout -> Bronze -> Silver --┐
População ----- validar layout -> Bronze -> Silver --┤
PIB ----------- validar layout -> Bronze -> Silver --┼-> validar Silver
IPCA ---------- validar layout -> Bronze -> Silver --┘        │
                                                              ▼
                                                   agregar e integrar Gold
                                                              │
                                                              ▼
                                                        validar Gold
                                                              │
                                                              ▼
                                                    arquivar Bronze válida
```

As quatro branches podem avançar em paralelo. A Gold só é criada após todas as quatro Silvers serem carregadas e aprovadas.

---

## 5. Ambiente GCP

### 5.1 Projeto

| Configuração | Valor |
|---|---|
| Project ID | `insightfuel-gzanini-2026` |
| Região de dados | `southamerica-east1` |
| Console do projeto | [Abrir dashboard](https://console.cloud.google.com/home/dashboard?project=insightfuel-gzanini-2026) |
| BigQuery | [Abrir BigQuery Studio](https://console.cloud.google.com/bigquery?project=insightfuel-gzanini-2026) |
| IAM | [Abrir IAM](https://console.cloud.google.com/iam-admin/iam?project=insightfuel-gzanini-2026) |
| APIs | [Abrir APIs e serviços](https://console.cloud.google.com/apis/dashboard?project=insightfuel-gzanini-2026) |

Este é um projeto próprio. Nenhum recurso foi criado no ambiente da FS.

### 5.2 Bucket Bronze

| Configuração | Valor |
|---|---|
| Bucket | `gs://insightfuel-gzanini-2026-bronze` |
| Região | `SOUTHAMERICA-EAST1` |
| Classe | `STANDARD` |
| Acesso uniforme | habilitado |
| Prevenção de acesso público | obrigatória/enforced |
| Soft delete | 7 dias |
| Console | [Abrir bucket](https://console.cloud.google.com/storage/browser/insightfuel-gzanini-2026-bronze?project=insightfuel-gzanini-2026) |

### 5.3 Datasets BigQuery

| Dataset | Função | Localização |
|---|---|---|
| `insightfuel_control` | auditoria e controle | `southamerica-east1` |
| `insightfuel_silver` | dados tratados por fonte | `southamerica-east1` |
| `insightfuel_gold` | visão analítica integrada | `southamerica-east1` |

Todos os datasets usam até 168 horas de time travel, conforme a configuração padrão observada.

---

## 6. Fontes de dados

| Fonte | Instituição | Granularidade | Papel no projeto | Página oficial |
|---|---|---|---|---|
| Preços de combustíveis | ANP | posto, produto e data | fonte principal | [Dados abertos ANP](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis) |
| População | IBGE | município e ano | dimensão demográfica | [Estimativas da população](https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-population.html) |
| PIB municipal | IBGE | município e ano | dimensão econômica | [PIB dos Municípios](https://www.ibge.gov.br/estatisticas/economicas/contas-nacionais/9088-produtointerno-bruto-dos-municipios.html) |
| IPCA | IBGE | ano e mês | dimensão macroeconômica | [IPCA e séries históricas](https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html) |

### 6.1 Formatos aceitos

| Fonte | Extensões aceitas |
|---|---|
| ANP | `.csv` |
| População | `.csv`, `.xls`, `.xlsx` |
| PIB | `.csv`, `.xlsx` |
| IPCA | `.csv`, `.xls`, `.xlsx` |

Arquivos ZIP não são ingeridos diretamente. Devem ser extraídos antes de serem colocados na pasta local da fonte.

### 6.2 Arquivos usados na execução completa

- ANP: cinco CSVs semestrais, de 2024.01 a 2026.01;
- população: `estimativa_dou_2024.xls`, `estimativa_dou_2025.xls` e `estimativa_dou_2026.xlsx`;
- PIB: `PIB dos Municípios - base de dados 2010-2023.xlsx`;
- IPCA: `ipca_202608SerieHist.xls`.

---

## 7. Estrutura do projeto

```text
insightfuel/
├── dags/
│   └── insightfuel_pipeline.py       # DAG, TaskGroups e dependências
├── src/insightfuel/
│   ├── __init__.py
│   ├── backends.py                   # GCS, BigQuery, schemas e qualidade
│   ├── config.py                     # leitura das Airflow Variables
│   ├── pipeline.py                   # casos de uso de cada etapa
│   └── transform.py                  # parsers, limpeza e deduplicação
├── tests/
│   └── test_pipeline.py              # oito testes unitários
├── data/
│   ├── input/
│   │   ├── anp/
│   │   ├── populacao/
│   │   ├── pib/
│   │   └── ipca/
│   └── samples/                      # arquivos pequenos de demonstração
├── scripts/
│   ├── start_airflow.ps1
│   ├── trigger_pipeline.ps1
│   └── stop_airflow.ps1
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── airflow_variables.example.json
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

### 7.1 Links para o código no diretório de trabalho

- [DAG](../dags/insightfuel_pipeline.py)
- [Configuração](../src/insightfuel/config.py)
- [Orquestração reutilizável](../src/insightfuel/pipeline.py)
- [Backend GCP](../src/insightfuel/backends.py)
- [Transformações](../src/insightfuel/transform.py)
- [Testes](../tests/test_pipeline.py)
- [Docker Compose](../docker-compose.yml)
- [README](../README.md)

---

## 8. Ambiente Docker e Airflow

### 8.1 Serviços

| Serviço | Imagem/base | Função |
|---|---|---|
| `postgres` | `postgres:16-alpine` | banco de metadados do Airflow |
| `airflow-webserver` | imagem construída localmente | interface web e API |
| `airflow-scheduler` | imagem construída localmente | agendamento e execução |
| `airflow-init` | mesma imagem Airflow | migração do banco e criação do usuário |

### 8.2 Configuração do Airflow

- versão base: `apache/airflow:2.10.5-python3.11`;
- executor: `LocalExecutor`;
- exemplos: desabilitados;
- DAGs novas: pausadas por padrão;
- banco: PostgreSQL;
- interface: `http://localhost:8081`;
- apenas uma execução ativa da DAG: `max_active_runs=1`;
- schedule: `None`, portanto disparo manual;
- catchup: desabilitado.

### 8.3 Dependências Python

| Pacote | Versão | Uso |
|---|---:|---|
| `google-cloud-storage` | 2.19.0 | upload, download, cópia e exclusão no GCS |
| `google-cloud-bigquery` | 3.20.1 | cargas, consultas e controle |
| `pandas` | 2.1.4 | leitura dos layouts oficiais do IBGE |
| `openpyxl` | 3.1.5 | leitura de XLSX |
| `xlrd` | 2.0.1 | leitura de XLS legado |

### 8.4 Volumes montados

```text
./dags       -> /opt/airflow/dags
./data/input -> /opt/airflow/input
./logs       -> /opt/airflow/logs
ADC local    -> /opt/airflow/secrets/application_default_credentials.json (somente leitura)
```

---

## 9. Configuração e Airflow Variables

As configurações são consumidas por `Variable.get` durante a execução das tasks. No Docker Compose, variáveis de ambiente com prefixo `AIRFLOW_VAR_` disponibilizam os valores ao Airflow.

| Airflow Variable | Obrigatória | Padrão/valor usado |
|---|---:|---|
| `insightfuel_input_root` | sim | `/opt/airflow/input` |
| `insightfuel_gcp_project_id` | sim | `insightfuel-gzanini-2026` |
| `insightfuel_gcs_bucket` | sim | `insightfuel-gzanini-2026-bronze` |
| `insightfuel_gcp_location` | não | `southamerica-east1` |
| `insightfuel_bq_silver_dataset` | não | `insightfuel_silver` |
| `insightfuel_bq_gold_dataset` | não | `insightfuel_gold` |
| `insightfuel_bq_control_dataset` | não | `insightfuel_control` |
| `insightfuel_bq_silver_table` | não | `silver_precos_anp` |
| `insightfuel_bq_population_table` | não | `silver_populacao_ibge` |
| `insightfuel_bq_pib_table` | não | `silver_pib_municipios_ibge` |
| `insightfuel_bq_ipca_table` | não | `silver_ipca_ibge` |
| `insightfuel_bq_gold_table` | não | `gold_precos_combustiveis_mensal` |
| `insightfuel_bq_control_table` | não | `ingestion_events` |
| `insightfuel_bronze_root` | não | `bronze` |
| `insightfuel_google_credentials_path` | não | caminho montado da ADC |

### 9.1 Variáveis do `.env`

```dotenv
AIRFLOW_UID=50000
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=troque-esta-senha
GCP_PROJECT_ID=seu-projeto-insightfuel
GCS_BUCKET=seu-bucket-insightfuel-bronze
GCP_LOCATION=southamerica-east1
GCP_ADC_PATH=C:/Users/seu_usuario/AppData/Roaming/gcloud/application_default_credentials.json
```

O `.env` real não é incluído no pacote nem versionado.

---

## 10. DAG e suas 16 tasks

### 10.1 TaskGroups por fonte

Cada fonte possui três tasks:

1. `<fonte>.validar_layout`;
2. `<fonte>.ingestao_bronze`;
3. `<fonte>.processar_silver`.

Quatro fontes × três tasks = 12 tasks.

### 10.2 Tasks comuns

13. `validar_silver`;
14. `gerar_gold`;
15. `validar_gold`;
16. `arquivar_bronze`.

### 10.3 Retentativas

| Task | Retentativas configuradas |
|---|---:|
| `validar_layout` | 1 |
| `ingestao_bronze` | 2 |
| `processar_silver` | 1 |
| `gerar_gold` | 1 |
| validações finais/archive | padrão do Airflow |

O `run_id` do Airflow é propagado para os caminhos do GCS e para a tabela de controle. Caracteres inseguros são substituídos por `_` na composição do caminho do objeto.

---

## 11. Processamento detalhado por etapa

### 11.1 `validar_layout`

1. Localiza arquivos compatíveis em `/opt/airflow/input/<fonte>`;
2. lê os arquivos ainda na pasta local;
3. valida cabeçalhos e campos obrigatórios;
4. converte e valida tipos;
5. normaliza texto e chaves;
6. remove duplicatas integrais;
7. verifica conflitos de chave;
8. registra um evento `layout/validated`.

Se ocorrer erro, todos os arquivos da fonte são enviados diretamente a `rejected/<run_id>` e são criados eventos `layout/rejected`. O arquivo inválido nunca entra em `incoming`.

### 11.2 `ingestao_bronze`

1. Recebe a lista de arquivos aprovados;
2. faz upload para `incoming/<run_id>`;
3. registra um evento `bronze/uploaded` por arquivo;
4. devolve as URIs `gs://...` via XCom.

### 11.3 `processar_silver`

1. Baixa novamente os objetos da Bronze;
2. repete parsing e validações;
3. substitui a tabela Silver da fonte com schema explícito;
4. usa `WRITE_TRUNCATE`;
5. registra `silver/loaded` e a quantidade de registros.

Se a leitura ou carga falhar, os objetos são movidos de `incoming` para `rejected`, o evento `silver/rejected` é registrado e a branch falha.

### 11.4 `validar_silver`

Para cada tabela Silver:

- exige contagem maior que zero;
- consulta o BigQuery depois da carga;
- reprova qualquer campo obrigatório nulo;
- também reprova strings obrigatórias vazias;
- registra `silver_quality/passed` com as contagens.

### 11.5 `gerar_gold`

1. agrega preços da ANP por ano, mês, UF, município e produto;
2. calcula média, mínimo, máximo, desvio padrão populacional e número de observações;
3. seleciona o registro populacional mais recente por código municipal;
4. seleciona o PIB mais recente por código municipal;
5. associa preço a população por UF e município normalizado;
6. associa população ao PIB por código IBGE;
7. associa IPCA por ano e mês;
8. substitui a tabela Gold com `WRITE_TRUNCATE`;
9. registra `gold/loaded`.

### 11.6 `validar_gold`

A Gold é reprovada quando:

- está vazia;
- `preco_minimo > preco_medio`;
- `preco_medio > preco_maximo`;
- `quantidade_observacoes <= 0`;
- código municipal está ausente;
- população está ausente;
- PIB ou PIB per capita está ausente;
- número-índice IPCA está ausente.

Em sucesso, registra `gold_quality/passed`.

### 11.7 `arquivar_bronze`

Somente depois da aprovação da Gold:

1. copia cada objeto de `incoming` para `archive`;
2. exclui a cópia de `incoming`;
3. registra `bronze/archived` com a URI final.

A operação é idempotente: se `incoming` já não existir, mas o destino em `archive` existir, a tarefa considera o objeto já movido e continua.

---

## 12. Contratos, schemas e regras por fonte

### 12.1 ANP

| Campo Silver | Tipo BigQuery | Obrigatório | Origem/transformação |
|---|---|---:|---|
| `cnpj_revenda` | STRING | sim | somente dígitos |
| `estabelecimento` | STRING | sim | maiúsculas |
| `uf` | STRING | sim | maiúsculas |
| `municipio` | STRING | sim | normalizado |
| `produto` | STRING | sim | maiúsculas |
| `data_coleta` | DATE | sim | entrada `DD/MM/AAAA` |
| `valor_venda` | FLOAT64 | sim | decimal positivo |
| `bandeira` | STRING | sim | maiúsculas |

Cabeçalhos reconhecidos incluem `CNPJ da Revenda`, `Revenda`/`Razão Social`, `Estado - Sigla`, `Município`, `Produto`, `Data da Coleta`, `Valor de Venda` e `Bandeira`.

Regras:

- CSV UTF-8 com BOM é aceito;
- delimitador `;` ou `,` é detectado por amostragem;
- vírgula e ponto decimal são aceitos;
- linhas completamente vazias são ignoradas;
- preço deve ser maior que zero;
- duplicatas integrais são removidas;
- identidade: CNPJ + produto + data + preço.

### 12.2 População

| Campo Silver | Tipo BigQuery | Obrigatório |
|---|---|---:|
| `codigo_municipio` | STRING | sim |
| `municipio` | STRING | sim |
| `uf` | STRING | sim |
| `ano` | INT64 | sim |
| `populacao` | INT64 | sim |

Regras do layout oficial:

- o ano é extraído do nome do arquivo, não do caminho completo;
- procura uma aba cujo nome contenha “município”;
- lê o cabeçalho oficial a partir da segunda linha;
- combina código da UF com código municipal, completando 2 + 5 dígitos;
- população deve ser positiva;
- chave: código municipal + ano.

### 12.3 PIB municipal

| Campo Silver | Tipo BigQuery | Obrigatório |
|---|---|---:|
| `codigo_municipio` | STRING | sim |
| `municipio` | STRING | sim |
| `uf` | STRING | sim |
| `ano` | INT64 | sim |
| `pib` | FLOAT64 | sim |
| `pib_per_capita` | FLOAT64 | sim |

O leitor usa a aba `PIB dos Municípios`, normaliza os nomes extensos das colunas oficiais e usa a chave código municipal + ano.

O arquivo oficial contém um PIB histórico negativo para Guamaré/RN em 2012. Esse valor é preservado, pois existe na própria fonte. A Gold seleciona o período mais recente de cada município, logo esse registro histórico não é usado como referência econômica atual.

### 12.4 IPCA

| Campo Silver | Tipo BigQuery | Obrigatório |
|---|---|---:|
| `ano` | INT64 | sim |
| `mes` | INT64 | sim |
| `numero_indice` | FLOAT64 | sim |
| `variacao_percentual` | FLOAT64 | sim |

O leitor da planilha histórica:

- identifica linhas que definem o ano corrente;
- converte JAN–DEZ para 1–12;
- extrai número-índice e variação mensal;
- ignora linhas de título e estrutura;
- usa ano + mês como chave.

### 12.5 Normalização municipal

A função de normalização:

- remove acentos por decomposição Unicode;
- remove apóstrofos sem introduzir espaço;
- substitui outros sinais por espaço;
- elimina espaços repetidos;
- converte para maiúsculas.

Exemplos:

```text
Sant'Ana do Livramento -> SANTANA DO LIVRAMENTO
Santana do Livramento  -> SANTANA DO LIVRAMENTO
Ji-Paraná              -> JI PARANA
Santa Bárbara d'Oeste  -> SANTA BARBARA DOESTE
```

Essa regra eliminou as últimas ausências de integração municipal encontradas durante o teste real.

---

## 13. Camada Bronze no GCS

### 13.1 Convenção de caminhos

```text
bronze/<fonte>/incoming/<run_id>/<arquivo>
bronze/<fonte>/archive/<run_id>/<arquivo>
bronze/<fonte>/rejected/<run_id>/<arquivo>
```

Fontes válidas para `<fonte>`:

```text
anp
populacao
pib
ipca
```

### 13.2 Significado dos estados

| Estado | Significado |
|---|---|
| `incoming` | arquivo validado, aguardando conclusão completa do pipeline |
| `archive` | arquivo processado em execução aprovada |
| `rejected` | arquivo reprovado no layout ou em processamento |

### 13.3 Histórico

O `run_id` impede sobrescrita entre execuções e permite reprocessar um snapshot bruto. A Bronze é o histórico permanente lógico; Silver e Gold representam apenas o snapshot mais recente.

---

## 14. Camada Silver no BigQuery

| Tabela | Organização física | Conteúdo |
|---|---|---|
| `insightfuel_silver.silver_precos_anp` | particionada por `data_coleta`; cluster `uf, municipio, produto` | observações tratadas de preço |
| `insightfuel_silver.silver_populacao_ibge` | cluster `uf, codigo_municipio` | população municipal anual |
| `insightfuel_silver.silver_pib_municipios_ibge` | cluster `uf, codigo_municipio` | PIB e PIB per capita anual |
| `insightfuel_silver.silver_ipca_ibge` | tabela simples | IPCA mensal |

### 14.1 Estratégia de carga

Cada carga usa schema explícito e `WRITE_TRUNCATE`. Consequências:

- repetir a mesma entrada não duplica registros;
- a tabela sempre representa o último snapshot processado;
- uma carga parcial de uma fonte substituiria apenas a Silver daquela fonte;
- o histórico dos arquivos continua preservado no GCS.

---

## 15. Camada Gold no BigQuery

### 15.1 Tabela

```text
insightfuel_gold.gold_precos_combustiveis_mensal
```

A tabela é agrupada fisicamente por `uf`, `municipio` e `produto`.

### 15.2 Schema

| Campo | Tipo | Descrição |
|---|---|---|
| `ano` | INTEGER | ano da coleta |
| `mes` | INTEGER | mês da coleta |
| `uf` | STRING | unidade federativa |
| `municipio` | STRING | município normalizado |
| `produto` | STRING | combustível |
| `preco_medio` | FLOAT | média mensal |
| `preco_minimo` | FLOAT | menor preço mensal |
| `preco_maximo` | FLOAT | maior preço mensal |
| `desvio_padrao_preco` | FLOAT | desvio padrão populacional |
| `quantidade_observacoes` | INTEGER | número de observações agregadas |
| `codigo_municipio` | STRING | código IBGE associado |
| `populacao` | INTEGER | população mais recente disponível |
| `pib` | FLOAT | PIB municipal mais recente |
| `pib_per_capita` | FLOAT | PIB per capita mais recente |
| `ipca_numero_indice` | FLOAT | número-índice do mês |
| `ipca_variacao_percentual` | FLOAT | variação mensal do IPCA |

### 15.3 Chaves de integração

```text
ANP -> população: UF + município normalizado
população -> PIB: código do município IBGE
ANP -> IPCA: ano + mês
```

### 15.4 Regra de referência temporal

Para população e PIB, a consulta aplica `ROW_NUMBER()` particionado por código municipal e ordenado por ano decrescente. O registro `rn = 1` é usado na Gold.

Na execução atual:

- população mais recente: 2026;
- PIB mais recente: 2023;
- IPCA associado exatamente pelo mês e ano do preço.

---

## 16. Controle de ingestão

### 16.1 Tabela

```text
insightfuel_control.ingestion_events
```

- particionamento diário: `event_ts`;
- clustering: `source`, `stage`, `status`;
- modelo: append-only.

### 16.2 Schema lógico

| Campo | Função |
|---|---|
| `event_id` | UUID exclusivo do evento |
| `run_id` | execução Airflow correlacionada |
| `source` | `anp`, `populacao`, `pib`, `ipca` ou `all` |
| `stage` | layout, bronze, silver, silver_quality, gold ou gold_quality |
| `status` | validated, uploaded, loaded, passed, rejected ou archived |
| `file_name` | nome do arquivo quando aplicável |
| `object_uri` | URI GCS quando aplicável |
| `row_count` | contagem da etapa |
| `event_ts` | timestamp UTC |
| `details` | métricas ou erro, limitado a 1.000 caracteres |

### 16.3 Eventos esperados

Uma execução simples com um arquivo por fonte gera normalmente 19 eventos. Uma execução com dez arquivos gera mais eventos individuais de upload e archive.

Retentativas ou reprocessamentos seletivos adicionam novos eventos porque a tabela é append-only. Isso é esperado e preserva toda a trilha técnica; para obter o estado mais recente, ordene por `event_ts` ou agrupe por `run_id`, fonte e etapa.

---

## 17. Qualidade, idempotência e tratamento de falhas

### 17.1 Barreiras de qualidade

```text
arquivo local
   │
   ├─ layout inválido ───────────────> rejected + evento + falha
   │
   ▼
incoming
   │
   ├─ transformação/carga inválida ──> rejected + evento + falha
   │
   ▼
Silver
   │
   ├─ vazia/campo obrigatório nulo ──> falha, Gold não é criada
   │
   ▼
Gold
   │
   ├─ métrica/join inválido ─────────> falha, Bronze não é arquivada
   │
   ▼
archive
```

### 17.2 Idempotência

- Silver: `WRITE_TRUNCATE` por fonte;
- Gold: `WRITE_TRUNCATE`;
- Bronze: novo diretório por `run_id`;
- archive: mover novamente um objeto já arquivado é aceito;
- controle: cumulativo por design.

### 17.3 Deduplicação

- ANP: duplicata integral removida; conflito da mesma identidade bloqueia a carga;
- população: código municipal + ano;
- PIB: código municipal + ano;
- IPCA: ano + mês;
- conflito de chave com conteúdo diferente gera erro.

---

## 18. Execução real e resultados

### 18.1 Identificação

```text
run_id: real_full_20260930_0140
estado final: success
tasks aprovadas: 16 de 16
```

### 18.2 Volumes

| Resultado | Registros | Cobertura |
|---|---:|---|
| Silver ANP | 2.125.555 | 2024-01-01 a 2026-06-30 |
| Silver população | 16.712 | 2024 a 2026 |
| Silver PIB | 77.965 | 2010 a 2023 |
| Silver IPCA | 392 | 1994-01 a 2026-08 |
| Gold | 62.071 | 2024 a 2026 |

Os cinco CSVs da ANP continham 2.134.685 linhas brutas, incluindo 9.114 linhas completamente vazias e duplicatas. A limpeza produziu 2.125.555 observações válidas.

### 18.3 Auditoria final

| Verificação | Resultado |
|---|---:|
| ANP: campos obrigatórios ausentes/inválidos | 0 |
| População: campos obrigatórios ausentes | 0 |
| PIB: campos obrigatórios ausentes | 0 |
| IPCA: campos obrigatórios ausentes | 0 |
| Gold: código municipal ausente | 0 |
| Gold: população ausente | 0 |
| Gold: PIB ausente | 0 |
| Gold: IPCA ausente | 0 |
| Gold: mínimo/médio/máximo incoerentes | 0 |

### 18.4 Estado do GCS

| Caminho da execução | Arquivos |
|---|---:|
| `archive/real_full_20260930_0140` | 10 |
| `incoming/real_full_20260930_0140` | 0 |
| `rejected/real_full_20260930_0140` | 3 |

Os três arquivos de população em `rejected` documentam uma falha inicial de interpretação do ano. A causa foi corrigida, os arquivos foram reprocessados e também constam corretamente em `archive`. As cópias rejeitadas não foram apagadas para preservar a auditoria.

### 18.5 Problemas encontrados e corrigidos

1. **Ano da população:** a primeira expressão regular capturava o ano existente no `run_id`; passou a analisar somente o nome-base do arquivo.
2. **Municípios divergentes:** `Sant'Ana do Livramento`, `Ji-Paraná` e `Santa Bárbara d'Oeste` exigiram normalização consistente entre ANP e IBGE.
3. **Preços diferentes no mesmo posto/data:** o preço foi incluído na identidade da observação ANP.
4. **Reprocessamento de archive:** a movimentação ficou idempotente quando o destino já existe.
5. **Qualidade Gold:** passou de métrica informativa para bloqueio de qualquer integração ausente.
6. **Qualidade Silver:** passou a consultar o BigQuery e bloquear campos obrigatórios nulos ou vazios após a carga.
7. **PIB negativo histórico:** confirmado diretamente no XLSX oficial e preservado como dado da fonte.

---

## 19. Testes automatizados

### 19.1 Casos cobertos

1. leitura dos quatro layouts CSV de amostra;
2. normalização equivalente de nomes municipais;
3. rejeição de coluna obrigatória ausente;
4. preservação de dois preços distintos do mesmo posto/produto/data;
5. leitura das Airflow Variables;
6. carga BigQuery com schema e `WRITE_TRUNCATE`;
7. rejeição antes de `incoming`;
8. registro da URI final de archive.

### 19.2 Resultado

```text
Ran 8 tests
OK
```

### 19.3 Executar os testes na imagem Docker

```powershell
docker compose run --rm -T `
  -v "${PWD}/tests:/opt/airflow/project/tests:ro" `
  airflow-webserver `
  python -m unittest discover -s /opt/airflow/project/tests -v
```

### 19.4 Verificar erros de importação

```powershell
docker compose exec -T airflow-webserver `
  airflow dags list-import-errors --output json
```

Resultado esperado:

```json
[]
```

---

## 20. Manual de operação

### 20.1 Pré-requisitos

- Windows com PowerShell;
- Docker Desktop em execução;
- Google Cloud CLI autenticado;
- Application Default Credentials existentes;
- acesso ao projeto GCP;
- arquivos colocados nas quatro pastas de entrada.

Links:

- [Docker Desktop](https://docs.docker.com/desktop/)
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc)

### 20.2 Autenticar a ADC

```powershell
gcloud auth application-default login
gcloud config set project insightfuel-gzanini-2026
```

### 20.3 Criar o `.env`

```powershell
Copy-Item .env.example .env
```

Editar:

- `GCP_PROJECT_ID`;
- `GCS_BUCKET`;
- `GCP_ADC_PATH`;
- senha administrativa local.

### 20.4 Preparar arquivos

```text
data/input/anp/
data/input/populacao/
data/input/pib/
data/input/ipca/
```

Não misture fontes na mesma pasta. Extraia ZIPs antes da execução.

### 20.5 Iniciar Airflow

```powershell
.\scripts\start_airflow.ps1
```

Equivalente:

```powershell
docker compose run --rm airflow-init
docker compose up -d --build airflow-webserver airflow-scheduler
docker compose ps
```

### 20.6 Abrir a interface

[Abrir Airflow local](http://localhost:8081)

Use o usuário e senha definidos no `.env`. No ambiente de desenvolvimento inicialmente testado foi usado `admin/admin`; troque a senha fora de uma demonstração local.

### 20.7 Disparar a DAG

```powershell
.\scripts\trigger_pipeline.ps1
```

Ou:

```powershell
docker compose exec -T airflow-scheduler `
  airflow dags unpause insightfuel_pipeline

docker compose exec -T airflow-scheduler `
  airflow dags trigger insightfuel_pipeline
```

### 20.8 Acompanhar

```powershell
docker compose logs -f airflow-scheduler
docker compose ps
```

Na interface, abra a DAG `insightfuel_pipeline` e use Graph ou Grid.

### 20.9 Consultar execuções

```powershell
docker compose exec -T airflow-webserver `
  airflow dags list-runs -d insightfuel_pipeline --output json
```

### 20.10 Parar

```powershell
.\scripts\stop_airflow.ps1
```

O script executa `docker compose down`. O volume PostgreSQL permanece, pois não é usado `-v`.

---

## 21. Consultas de auditoria

Substitua o `run_id` quando necessário.

### 21.1 Contagens das tabelas

```sql
SELECT 'silver_anp' tabela, COUNT(*) registros
FROM `insightfuel-gzanini-2026.insightfuel_silver.silver_precos_anp`
UNION ALL
SELECT 'silver_populacao', COUNT(*)
FROM `insightfuel-gzanini-2026.insightfuel_silver.silver_populacao_ibge`
UNION ALL
SELECT 'silver_pib', COUNT(*)
FROM `insightfuel-gzanini-2026.insightfuel_silver.silver_pib_municipios_ibge`
UNION ALL
SELECT 'silver_ipca', COUNT(*)
FROM `insightfuel-gzanini-2026.insightfuel_silver.silver_ipca_ibge`
UNION ALL
SELECT 'gold', COUNT(*)
FROM `insightfuel-gzanini-2026.insightfuel_gold.gold_precos_combustiveis_mensal`;
```

### 21.2 Qualidade Gold

```sql
SELECT
  COUNT(*) AS registros,
  COUNTIF(codigo_municipio IS NULL OR codigo_municipio = '') AS sem_municipio,
  COUNTIF(populacao IS NULL) AS sem_populacao,
  COUNTIF(pib IS NULL OR pib_per_capita IS NULL) AS sem_pib,
  COUNTIF(ipca_numero_indice IS NULL) AS sem_ipca,
  COUNTIF(
    preco_minimo > preco_medio
    OR preco_medio > preco_maximo
    OR quantidade_observacoes <= 0
  ) AS metricas_invalidas
FROM `insightfuel-gzanini-2026.insightfuel_gold.gold_precos_combustiveis_mensal`;
```

### 21.3 Eventos de uma execução

```sql
SELECT *
FROM `insightfuel-gzanini-2026.insightfuel_control.ingestion_events`
WHERE run_id = 'real_full_20260930_0140'
ORDER BY event_ts;
```

### 21.4 Último estado por etapa

```sql
SELECT * EXCEPT(rn)
FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY run_id, source, stage, file_name
    ORDER BY event_ts DESC
  ) AS rn
  FROM `insightfuel-gzanini-2026.insightfuel_control.ingestion_events`
)
WHERE rn = 1
ORDER BY event_ts;
```

### 21.5 Listar o histórico da Bronze

```powershell
gcloud storage ls --recursive `
  gs://insightfuel-gzanini-2026-bronze/bronze/**
```

### 21.6 Confirmar que uma execução saiu de incoming

```powershell
gcloud storage ls --recursive `
  gs://insightfuel-gzanini-2026-bronze/bronze/** `
  | Select-String 'real_full_20260930_0140'
```

---

## 22. Segurança e credenciais

### 22.1 Implementado

- credencial ADC montada somente para leitura;
- caminho da credencial, não o JSON, informado ao container;
- `.env` ignorado pelo Git e Docker build context;
- credenciais não incluídas no ZIP;
- bucket com prevenção de acesso público;
- acesso uniforme no bucket;
- interface Airflow exposta somente em `127.0.0.1:8081`;
- banco PostgreSQL não exposto ao host.

### 22.2 Recomendações

- alterar a senha padrão antes de qualquer exposição de rede;
- usar conta de serviço com privilégios mínimos em ambiente compartilhado;
- limitar permissões a leitura/escrita no bucket e datasets necessários;
- não copiar o conteúdo da chave JSON para Airflow Variables;
- rotacionar qualquer credencial acidentalmente exposta;
- em produção, usar identidade do workload em vez de chave local.

---

## 23. Limitações conhecidas e evolução

### 23.1 Limitações atuais

1. **Aquisição manual:** o usuário baixa e extrai os arquivos para a pasta local.
2. **Sem schedule:** a DAG é disparada manualmente.
3. **Snapshot analítico:** Silver e Gold são substituídas, não versionadas.
4. **Memória local:** arquivos são transformados em Python antes da carga; volumes muito maiores podem exigir processamento por chunks.
5. **`load_table_from_json`:** funcionou para a entrega, mas uma solução produtiva poderia usar Parquet no GCS e jobs nativos do BigQuery.
6. **Controle append-only:** retentativas geram eventos adicionais; as consultas devem considerar timestamp.
7. **Sem IaC:** bucket, datasets e tabela de controle não são recriados automaticamente pelo pacote.
8. **Sem Power BI:** consumo visual ainda será desenvolvido.
9. **LocalExecutor:** adequado à entrega local, não a alta disponibilidade.

### 23.2 Próximas evoluções sugeridas

- download automático das páginas oficiais;
- checksum e tamanho do arquivo no controle;
- manifesto de ingestão para bloquear arquivo já processado independentemente do `run_id`;
- cargas incrementais com `MERGE`;
- arquivos intermediários Parquet;
- Dataform/dbt para transformações SQL;
- alertas por e-mail/Teams em falhas;
- agendamento por frequência de cada fonte;
- infraestrutura como código com Terraform;
- service account dedicada;
- testes de integração automatizados em um projeto GCP de desenvolvimento;
- dashboard Power BI conectado à Gold;
- dimensões calendário, município e produto dedicadas.

### 23.3 Sugestão para Power BI

Conectar o Power BI ao BigQuery e usar `gold_precos_combustiveis_mensal` para:

- evolução do preço médio por produto;
- comparação entre UFs e municípios;
- mínimo, máximo e dispersão;
- preço versus população;
- preço versus PIB per capita;
- preço versus IPCA;
- ranking municipal;
- filtros por ano, mês, UF, município e produto.

---

## 24. Troubleshooting

### 24.1 Docker não inicia

```powershell
docker info
docker compose config
docker compose ps
```

Confirme que o Docker Desktop está aberto e que a porta 8081 não está ocupada.

### 24.2 Airflow não encontra credencial

Verifique `GCP_ADC_PATH` no `.env` e confirme que o arquivo existe no Windows. Dentro do container, o caminho esperado é:

```text
/opt/airflow/secrets/application_default_credentials.json
```

### 24.3 Arquivo não encontrado

Confirme pasta, extensão e volume:

```powershell
Get-ChildItem data\input -Recurse -File
docker compose exec -T airflow-webserver `
  find /opt/airflow/input -maxdepth 2 -type f
```

### 24.4 Layout rejeitado

1. abra o log da task `validar_layout`;
2. consulte `ingestion_events` com status `rejected`;
3. verifique o objeto em `bronze/<fonte>/rejected/<run_id>`;
4. confira nomes das colunas, aba e extensão.

### 24.5 Gold falha por integração

Liste municípios sem correspondência:

```sql
SELECT uf, municipio, COUNT(*) linhas
FROM `insightfuel-gzanini-2026.insightfuel_gold.gold_precos_combustiveis_mensal`
WHERE codigo_municipio IS NULL
GROUP BY uf, municipio
ORDER BY linhas DESC;
```

Investigue diferenças de grafia entre `silver_precos_anp` e `silver_populacao_ibge`.

### 24.6 Reexecutar sem duplicar

Coloque novamente os arquivos de entrada e dispare uma nova execução. O novo `run_id` cria outro histórico na Bronze, enquanto Silver e Gold são substituídas sem duplicação.

### 24.7 Objeto já arquivado

A função de movimentação aceita o destino existente. Se origem e destino não existirem, a task falha para evitar perda silenciosa.

---

## 25. Links úteis

### 25.1 Projeto e ferramentas locais

- [Airflow local](http://localhost:8081)
- [Console do projeto GCP](https://console.cloud.google.com/home/dashboard?project=insightfuel-gzanini-2026)
- [Bucket Bronze](https://console.cloud.google.com/storage/browser/insightfuel-gzanini-2026-bronze?project=insightfuel-gzanini-2026)
- [BigQuery Studio](https://console.cloud.google.com/bigquery?project=insightfuel-gzanini-2026)
- [Logs do projeto no Cloud Logging](https://console.cloud.google.com/logs/query?project=insightfuel-gzanini-2026)
- [IAM](https://console.cloud.google.com/iam-admin/iam?project=insightfuel-gzanini-2026)
- [Quotas](https://console.cloud.google.com/iam-admin/quotas?project=insightfuel-gzanini-2026)

### 25.2 Fontes oficiais

- [ANP — Série Histórica de Preços de Combustíveis e GLP](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis)
- [ANP — Série histórica do levantamento de preços](https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos)
- [IBGE — Estimativas da população](https://www.ibge.gov.br/estatisticas/sociais/populacao/9103-estimativas-de-population.html)
- [IBGE — PIB dos Municípios](https://www.ibge.gov.br/estatisticas/economicas/contas-nacionais/9088-produtointerno-bruto-dos-municipios.html)
- [IBGE — IPCA](https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html)
- [SIDRA/IBGE](https://sidra.ibge.gov.br/)

### 25.3 Documentação técnica

- [Apache Airflow 2.10.5](https://airflow.apache.org/docs/apache-airflow/2.10.5/)
- [Airflow TaskFlow API](https://airflow.apache.org/docs/apache-airflow/stable/tutorial/taskflow.html)
- [Airflow Variables](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/variables.html)
- [Docker Compose](https://docs.docker.com/compose/)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)
- [Python Client for Cloud Storage](https://cloud.google.com/python/docs/reference/storage/latest)
- [BigQuery](https://cloud.google.com/bigquery/docs)
- [Python Client for BigQuery](https://cloud.google.com/python/docs/reference/bigquery/latest)
- [BigQuery partitioned tables](https://cloud.google.com/bigquery/docs/partitioned-tables)
- [BigQuery clustered tables](https://cloud.google.com/bigquery/docs/clustered-tables)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
- [pandas `read_excel`](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)
- [openpyxl](https://openpyxl.readthedocs.io/)
- [xlrd](https://xlrd.readthedocs.io/)
- [Power BI com BigQuery](https://learn.microsoft.com/power-query/connectors/google-bigquery)

---

## 26. Glossário

| Termo | Definição |
|---|---|
| ADC | Application Default Credentials do Google Cloud |
| ANP | Agência Nacional do Petróleo, Gás Natural e Biocombustíveis |
| BQ | BigQuery |
| Bronze | camada de arquivos brutos |
| DAG | grafo direcionado de tarefas do Airflow |
| GCS | Google Cloud Storage |
| Gold | camada integrada para consumo analítico |
| IBGE | Instituto Brasileiro de Geografia e Estatística |
| Idempotência | repetir uma operação sem produzir duplicação indevida |
| IPCA | Índice Nacional de Preços ao Consumidor Amplo |
| `run_id` | identificador único de uma execução Airflow |
| Silver | camada tratada e padronizada |
| XCom | mecanismo do Airflow para passar resultados entre tasks |

---

## Conclusão

O projeto implementado atende e supera os requisitos mínimos da Entrega 3. As quatro fontes planejadas estão operacionais, o pipeline foi executado com os arquivos completos disponíveis, as camadas Bronze, Silver, Gold e Controle estão materializadas na GCP, as validações bloqueiam dados incompletos e a estratégia de reprocessamento evita duplicação nas tabelas analíticas.

A entrega atual pode ser demonstrada integralmente no Airflow, GCS e BigQuery. A próxima evolução natural é a construção do relatório Power BI sobre a tabela Gold.
