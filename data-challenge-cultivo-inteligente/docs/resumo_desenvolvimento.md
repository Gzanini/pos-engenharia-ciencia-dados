# Desenvolvimento da Recomendacao de Cultivo Inteligente

## Materiais da Entrega 1

A primeira entrega e composta pelo relatorio `docs/Data challenge - Diego Torales e Guilherme Zanini.pdf` e pelo notebook executado `notebooks/00_analise_exploratoria_inicial.ipynb`. O notebook foi preparado como uma analise inicial autocontida: apresenta o problema, documenta a aquisicao via API, resume o dicionario dos dados, verifica qualidade, explora distribuicoes e relacoes e encerra com um experimento simples de viabilidade, principais confusoes e analise de sensibilidade.

O notebook `notebooks/01_analise_modelagem_cultivo.ipynb` nao foi removido. Ele permanece como versao tecnica mais completa para as proximas etapas, com matriz de confusao, importancia de atributos, analise de sensibilidade e exportacao do modelo.

## Problema e objetivo

O projeto busca classificar uma cultura agricola entre 22 possibilidades a partir de sete atributos de solo e microclima. O modelo deve identificar a classe mais compativel com os padroes da base analisada. A saida nao permite afirmar qual cultura maximiza produtividade ou retorno financeiro em uma regiao, pois o dataset nao contem localizacao, periodo, produtividade, custos ou precos.

## Base e qualidade dos dados

A base `randalakab/Crop-recommendation` foi adquirida por meio da API do Hugging Face. O grupo realizou o acesso e a analise do conjunto publico, nao a coleta original das medicoes agricolas. A base possui 2.200 registros e oito colunas: sete variaveis preditoras e a cultura recomendada. As 22 classes possuem 100 observacoes cada. Nao foram encontrados valores ausentes nem linhas duplicadas.

Foram identificados 19 registros com umidade superior a 100%. Eles foram mantidos no cenario principal porque a origem e a unidade da variavel ainda precisam ser confirmadas. Uma analise de sensibilidade foi executada separadamente.

## Estrategia de avaliacao

O conjunto foi dividido de forma estratificada, com 80% dos registros para treino e 20% para teste. O baseline, a regressao logistica, a arvore de decisao e o Random Forest foram comparados por validacao cruzada estratificada com cinco particoes no conjunto de treino. O criterio de selecao foi o F1 macro medio. O teste permaneceu reservado ate a escolha do modelo.

## Primeiro experimento

| Modelo | F1 macro medio | Desvio-padrao |
|---|---:|---:|
| Random Forest | 0,9652 | 0,0069 |
| Regressao logistica | 0,9254 | 0,0108 |
| Arvore de decisao | 0,9096 | 0,0067 |
| Baseline | 0,0040 | 0,0000 |

O Random Forest apresentou o melhor resultado na validacao cruzada. No teste reservado, obteve acuracia de 0,9727 e F1 macro de 0,9725. O modelo errou 12 das 440 observacoes, com maior concentracao de confusoes entre `kidneybeans` e `chickpea`.

No Random Forest, as maiores importancias foram observadas para umidade, fosforo, precipitacao e nitrogenio. Essas importancias descrevem o uso das variaveis pelo modelo e nao estabelecem relacao causal.

## Sensibilidade da umidade

| Cenario | Registros | F1 macro medio |
|---|---:|---:|
| Base completa | 2.200 | 0,9680 |
| Sem umidade acima de 100% | 2.181 | 0,9712 |

A diferenca de desempenho foi pequena. Esse resultado nao resolve a duvida sobre a validade fisica dos valores. A decisao de corrigir ou excluir registros depende da documentacao da base.

## Limites e continuidade

O desempenho elevado e interno ao dataset. A continuidade do projeto deve priorizar a proveniencia dos dados, o dicionario de variaveis, o ajuste controlado de hiperparametros e a analise dos erros. Para uso pratico, sera necessario testar o modelo com dados locais de solo e clima e submeter as recomendacoes a validacao agronomica.

## Ambiente reproduzivel

Foram adicionados `Dockerfile`, `docker-compose.yml` e `.dockerignore`. O conteiner utiliza Python 3.12, instala as dependencias de `requirements.txt`, monta a pasta do projeto em `/workspace` e disponibiliza o JupyterLab na porta `8888`.

Comandos principais:

```bash
docker compose up --build -d
docker compose ps
```

O ambiente pode ser acessado em `http://localhost:8888`. A execucao automatizada do notebook usado na entrega pode ser repetida com:

```bash
docker compose exec jupyter jupyter nbconvert \
  --to notebook --execute --inplace \
  notebooks/00_analise_exploratoria_inicial.ipynb \
  --ExecutePreprocessor.timeout=900
```

Para finalizar o ambiente:

```bash
docker compose down
```

Na validacao realizada em 5 de novembro de 2026, o notebook apresentou 29 celulas, sendo 14 de codigo, todas executadas sem erro. O JupyterLab respondeu normalmente na porta configurada e os resultados do experimento permaneceram coerentes com o relatorio: F1 macro medio de 0,9652 na validacao cruzada, F1 macro de 0,9725 no conjunto de teste e sensibilidade de 0,9680 para 0,9712 para o Random Forest.

