# Guia da DAG InsightFuel — Entrega 3

## Resultado da implementação

A DAG `insightfuel_pipeline` implementa as quatro ingestões previstas no projeto: preços da ANP, população, PIB municipal e IPCA. Ela opera diretamente no projeto GCP `insightfuel-gzanini-2026`, usando GCS para Bronze e BigQuery para Controle, Silver e Gold. Power BI foi mantido fora desta etapa.

## Conferência com o projeto e a atividade

| Requisito | Implementação | Situação |
|---|---|---|
| Pipeline funcional no Apache Airflow | Docker local com webserver, scheduler e PostgreSQL | atendido |
| Pelo menos três etapas encadeadas | validação, Bronze, Silver, validação conjunta, Gold, validação Gold e archive | superado |
| Quatro fontes definidas no mapeamento | ANP, população, PIB municipal e IPCA | atendido |
| Bronze original e rastreável no GCS | `incoming`, `archive` e `rejected` por fonte e `run_id` | atendido |
| Silver limpa e padronizada no BigQuery | quatro tabelas com tipagem, deduplicação e campos obrigatórios | atendido |
| Gold agregada e integrada | preços mensais com população, PIB, PIB per capita e IPCA | atendido |
| Qualidade e idempotência recomendadas | validações bloqueantes e `WRITE_TRUNCATE` nas tabelas analíticas | atendido |
| Consumo no Power BI | Gold pronta para conexão | adiado por decisão de escopo |

O desenho original propunha `CNPJ + produto + data` como chave da ANP. Na carga oficial foram encontradas quatro combinações válidas com dois preços distintos no mesmo posto, produto e data. Por isso, o preço observado passou a integrar a identidade da observação: duplicatas integrais continuam removidas, mas medições distintas não são descartadas. Esse é um refinamento orientado pelos dados reais, não a retirada de um requisito.

## Desenho executado

Para cada fonte há três tasks independentes e paralelizáveis:

1. `validar_layout`: valida o arquivo ainda na pasta local;
2. `ingestao_bronze`: grava o arquivo válido no GCS em `incoming/<run_id>`;
3. `processar_silver`: relê o objeto do GCS, repete a validação e substitui a Silver da fonte.

Após as quatro branches:

4. `validar_silver` confirma que todas as tabelas têm dados;
5. `gerar_gold` agrega os preços e integra população, PIB e IPCA;
6. `validar_gold` verifica as métricas finais;
7. `arquivar_bronze` move os arquivos da execução para o histórico.

No total, o gráfico possui 16 tasks.

```text
ANP ----------- validar -> Bronze -> Silver --┐
População ----- validar -> Bronze -> Silver --┤
PIB ----------- validar -> Bronze -> Silver --┼-> validar Silver -> Gold -> validar Gold -> archive
IPCA ---------- validar -> Bronze -> Silver --┘
```

## Organização da Bronze

```text
bronze/anp/{incoming,archive,rejected}/<run_id>/
bronze/populacao/{incoming,archive,rejected}/<run_id>/
bronze/pib/{incoming,archive,rejected}/<run_id>/
bronze/ipca/{incoming,archive,rejected}/<run_id>/
```

O layout é verificado antes de `incoming`. Um arquivo inválido vai diretamente para `rejected`, com a causa registrada. Após sucesso completo, o objeto é copiado para `archive` e removido de `incoming`. O `run_id` preserva versões históricas da Bronze.

## Controle de ingestão

A tabela `insightfuel_control.ingestion_events` mantém um log append-only por execução. Ela registra a fonte, etapa, status, arquivo, URI GCS, quantidade de linhas, horário e detalhes de erro/métricas.

Uma execução normal com um arquivo por fonte produz 19 eventos:

- 4 layouts validados;
- 4 uploads para Bronze;
- 4 cargas Silver;
- 1 validação conjunta da Silver;
- 1 carga Gold;
- 1 validação Gold;
- 4 arquivamentos com o URI final.

## Tabelas produzidas

| Camada | Tabela | Conteúdo |
|---|---|---|
| Controle | `insightfuel_control.ingestion_events` | rastreabilidade por `run_id` |
| Silver | `insightfuel_silver.silver_precos_anp` | preços tratados |
| Silver | `insightfuel_silver.silver_populacao_ibge` | população municipal |
| Silver | `insightfuel_silver.silver_pib_municipios_ibge` | PIB e PIB per capita |
| Silver | `insightfuel_silver.silver_ipca_ibge` | índice e variação mensal |
| Gold | `insightfuel_gold.gold_precos_combustiveis_mensal` | preços mensais integrados aos indicadores |

A integração municipal usa o código do município obtido na população e associado ao PIB. O IPCA é ligado por ano e mês. A Gold mantém as dimensões ano, mês, UF, município e produto.

## Regras de qualidade

- presença de todas as colunas obrigatórias;
- rejeição de campos obrigatórios vazios;
- tipagem de ano, mês, datas, população, PIB, índices e preços;
- preço e população positivos;
- PIB e PIB per capita numéricos, preservando valores históricos negativos existentes na fonte oficial;
- mês do IPCA entre 1 e 12;
- deduplicação integral;
- rejeição de chaves de negócio conflitantes;
- Silver de todas as fontes não vazia;
- Gold não vazia, com quantidade positiva e `mínimo <= médio <= máximo`;
- reprovação de registros Gold sem código municipal, população, PIB ou IPCA.

## Idempotência e histórico

Silver e Gold usam `WRITE_TRUNCATE`, portanto representam o snapshot mais recente sem duplicação. A Bronze não é sobrescrita: cada execução ganha seu próprio diretório em `archive/<run_id>`. A tabela de controle também é cumulativa.

## Evidência da execução real completa

A execução `real_full_20260930_0140` processou os dez arquivos oficiais disponíveis e concluiu as 16 tasks em `success`.

| Resultado | Linhas finais |
|---|---:|
| Silver ANP | 2.125.555 |
| Silver população | 16.712 |
| Silver PIB | 77.965 |
| Silver IPCA | 392 |
| Gold integrada | 62.071 |

Os preços cobrem 2024-01-01 a 2026-06-30; a população, 2024 a 2026; o PIB, 2010 a 2023; e o IPCA, 1994-01 a 2026-08. As quatro Silver não possuem campos obrigatórios vazios. O único PIB negativo do histórico é preservado porque consta assim na fonte oficial; ele é de 2012 e não é o período mais recente usado na Gold. A Gold não possui associações ausentes de município, população, PIB ou IPCA nem incoerências entre preço mínimo, médio e máximo.

Os dez arquivos válidos estão em `archive/real_full_20260930_0140` e não restou nenhum arquivo dessa execução em `incoming`. As três cópias de população em `rejected` documentam uma falha de leitura detectada durante o primeiro processamento; após a correção, os mesmos arquivos foram aceitos e arquivados. Essa trilha foi mantida deliberadamente para demonstrar rastreabilidade.

Os arquivos aceitos foram: cinco CSVs da ANP, dois XLS e um XLSX de população, um XLSX de PIB municipal e um XLS de IPCA. O pacote de entrega inclui código e amostras pequenas, não os arquivos oficiais volumosos nem credenciais.

## Como demonstrar

1. Abrir `http://localhost:8081` com `admin/admin`.
2. Abrir a DAG `insightfuel_pipeline` e mostrar o Graph com 16 tasks.
3. Colocar os arquivos nas pastas `data/input/<fonte>`: ANP em CSV, população em CSV/XLS/XLSX, PIB em CSV/XLSX e IPCA em CSV/XLS/XLSX.
4. Executar `.\scripts\trigger_pipeline.ps1`.
5. Mostrar os objetos em `bronze/<fonte>/archive/<run_id>`.
6. Consultar `insightfuel_control.ingestion_events` pelo `run_id`.
7. Mostrar as quatro Silver e a Gold integrada no BigQuery.

## Escopo deliberadamente adiado

Power BI não foi implementado agora. A Gold já está preparada como camada de consumo para essa próxima etapa.
