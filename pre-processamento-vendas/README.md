# Projeto Final - Pré-processamento de Dados em Vendas

Este repositório reúne a entrega final da disciplina de Pré-processamento de Dados. O foco é demonstrar, de ponta a ponta, como uma base bruta de vendas pode ser transformada em uma base tratada, confiável e analiticamente útil.

O trabalho foi pensado como um fluxo real de ciência de dados: primeiro entendemos o problema de negócio, depois inspecionamos os dados, tratamos inconsistências, criamos variáveis analíticas e consolidamos os resultados em notebooks reprodutíveis.

## Visão geral

O projeto responde à seguinte pergunta:

**Como preparar uma base confiável para analisar vendas, mix de produtos, comportamento temporal e concentração de receita?**

A partir dessa pergunta, o pipeline foi organizado para:

- integrar dados brutos de diferentes fontes;
- identificar nulos, duplicidades, inconsistências e outliers;
- limpar e padronizar a base;
- criar features úteis para análise;
- gerar visualizações e um resumo executivo final.

## Fontes de dados

Os dados utilizados estão em `dados/raw/` e incluem:

- arquivos JSON com movimentações diárias;
- arquivo CSV com cadastro de produtos e serviços.

Essas fontes foram combinadas para compor uma visão mais completa do contexto de vendas.

## Resultado do pipeline

Ao final do pré-processamento, o projeto consolidou uma base com:

- **667 registros válidos**;
- período analisado de **2026-05-01 a 2026-05-12**;
- **143 produtos distintos**;
- **receita líquida total de 54.264,98**;
- **46 outliers de receita** detectados pelo critério do IQR;
- **67,02% das vendas concentradas em final de semana**;
- presença de descontos em parte das transações;
- forte concentração de receita em poucos produtos.

Esses números mostram que o pré-processamento foi decisivo para transformar os dados em uma base confiável para leitura executiva.

## Principais entregáveis

- `notebooks/01_ingestao_limpeza.ipynb`
  - ingestão, diagnóstico e limpeza;
- `notebooks/02_transformacao_analise.ipynb`
  - transformação, análise e síntese executiva;
- `dados/processed/`
  - base tratada em CSV;
- `figures/`
  - gráficos gerados no processo analítico;
- `grupo.txt`
  - identificação do participante;
- `roteiro_video.md`
  - roteiro resumido para gravação;
- `explicacao_completa_projeto.md`
  - guia detalhado para estudo e apresentação.

## Estrutura do repositório

```text
pre-processamento-vendas/
  docker-compose.yml
  docker/
    jupyter/
      Dockerfile
      requirements.txt
  dados/
    raw/
    processed/
  figures/
  notebooks/
    01_ingestao_limpeza.ipynb
    02_transformacao_analise.ipynb
  scripts/
    run_pipeline.py
  src/
    vendas_pipeline.py
  roteiro_video.md
  explicacao_completa_projeto.md
  grupo.txt
  README.md
```

## Como executar

1. Suba o ambiente com Docker:
   ```bash
   docker compose up --build -d
   ```

2. Acesse o Jupyter:
   - `http://localhost:8888`
   - token: `python@2026`

3. Execute o pipeline, se desejar refazer as saídas:
   ```bash
   python scripts/run_pipeline.py
   ```

4. Abra os notebooks na ordem:
   - `notebooks/01_ingestao_limpeza.ipynb`
   - `notebooks/02_transformacao_analise.ipynb`

## Organização lógica da entrega

1. Entendimento do problema de negócio.
2. Ingestão e diagnóstico da base bruta.
3. Limpeza e padronização dos dados.
4. Transformação e engenharia de features.
5. Visualização e interpretação dos resultados.
6. Consolidação final da entrega.

## Observações

- O projeto foi estruturado para ser reprodutível.
- O Docker foi mantido para facilitar a execução dos notebooks.
- O conteúdo textual dos notebooks foi revisado para um padrão mais adequado a uma entrega de pós-graduação.
- O roteiro e o guia detalhado ajudam na gravação e na apresentação final.
