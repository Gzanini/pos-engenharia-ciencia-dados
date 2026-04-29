# Análise Exploratória da Qualidade do Ar (EPA) - New York (2025)

## Disciplina
Introdução a Python

## Objetivo
Realizar uma análise exploratória de dados (EDA) sobre qualidade do ar da cidade de New York em 2025, utilizando dados públicos da EPA (Daily Summary Data).

## Fonte de dados
- EPA AirData: https://aqs.epa.gov/aqsweb/airdata/download_files.html
- Arquivo utilizado: `daily_44201_2025.zip` (parâmetro 44201 - Ozone)

## Conteúdo do projeto
- `analise_qualidade_ar_epa_new_york_2025.ipynb`: notebook principal com limpeza, análise, gráficos, interpretação e conclusão.
- `analise_qualidade_ar_epa_new_york_2025.pdf`: versão em PDF com saídas para entrega.
- `requirements.txt`: dependências do ambiente Python.
- `entrega_moodle_resumo.md`: resumo dos requisitos da entrega no Moodle.

## Principais etapas realizadas
1. Importação de bibliotecas (`pandas`, `numpy`, `matplotlib`, `seaborn`).
2. Leitura do CSV a partir do arquivo `.zip`.
3. Padronização dos nomes de colunas.
4. Tratamento de dados:
- conversão de `date_local` para datetime
- tratamento de valores nulos
- filtro para cidade `New York`
5. Estatística descritiva do AQI (Índice de Qualidade do Ar).
6. Visualizações:
- AQI ao longo do tempo (linha)
- AQI médio por mês (barras)
- Distribuição do AQI (histograma)
7. Interpretação dos resultados e conclusão.

## Como executar
1. Criar e ativar ambiente virtual.
2. Instalar dependências:

```bash
pip install -r requirements.txt
```

3. Abrir o notebook no VSCode/Jupyter e executar as células em ordem.

## Observação
Este dataset (`44201`) é específico para ozônio (Ozone), por isso não há comparação entre múltiplos poluentes dentro deste mesmo arquivo.
