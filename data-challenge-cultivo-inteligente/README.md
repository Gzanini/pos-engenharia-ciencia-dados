# Data Challenge - Recomendacao de Cultivo Inteligente

Projeto da disciplina `2026/2 - Data Challenge - LT96012-00004-1000006`.

O trabalho desenvolve um classificador multiclasse para recomendar uma cultura agricola a partir de atributos do solo e do microclima. A recomendacao representa compatibilidade com os padroes observados na base de treinamento. O resultado nao substitui validacao agronomica nem permite estimar produtividade ou retorno financeiro.

## Problema do projeto

A pergunta central e:

**Em que medida os teores de nitrogenio, fosforo e potassio, combinados com temperatura, umidade, pH e precipitacao, permitem identificar a cultura mais compativel entre as 22 classes da base?**

## Fonte de dados

O notebook consulta a API do Hugging Face para localizar o arquivo publicado no dataset [`randalakab/Crop-recommendation`](https://huggingface.co/datasets/randalakab/Crop-recommendation).

O grupo realizou a aquisicao e a analise da base publica, nao a coleta original das medicoes agricolas. A fonte consultada nao documenta de forma suficiente a regiao, o periodo, o metodo de coleta e as unidades de todas as variaveis.

A base analisada possui:

- 2.200 registros;
- sete variaveis preditoras;
- 22 culturas, com 100 observacoes por classe;
- nenhum valor ausente;
- nenhuma linha duplicada;
- 19 registros com umidade acima de 100%.

O notebook pode usar `data/crop_recommendation.csv` como contingencia quando a API estiver indisponivel. O arquivo local nao e necessario para a execucao normal.

## Metodologia

1. Inspecao do esquema, tipos, valores ausentes, duplicidades e extremos.
2. Analise descritiva e visual das variaveis.
3. Separacao estratificada de 80% para treino e 20% para teste.
4. Comparacao de baseline, regressao logistica, arvore de decisao e Random Forest.
5. Validacao cruzada estratificada com cinco particoes apenas no conjunto de treino.
6. Selecao do modelo pelo F1 macro medio.
7. Avaliacao final no conjunto de teste reservado.
8. Analise de sensibilidade para os registros com umidade acima de 100%.

## Resultados preliminares

| Modelo | F1 macro medio na validacao cruzada | Desvio-padrao |
|---|---:|---:|
| Random Forest | 0,9652 | 0,0069 |
| Regressao logistica | 0,9254 | 0,0108 |
| Arvore de decisao | 0,9096 | 0,0067 |
| Baseline | 0,0040 | 0,0000 |

O Random Forest foi selecionado. No conjunto de teste reservado, obteve acuracia de 0,9727 e F1 macro de 0,9725. Foram 12 classificacoes incorretas em 440 observacoes. A confusao mais frequente ocorreu entre `kidneybeans` e `chickpea`.

Essas metricas sao preliminares e medem o desempenho interno nesta base. Como o dataset nao informa local, data, metodo de coleta ou unidade documentada de todas as variaveis, o resultado nao demonstra generalizacao para uma regiao agricola real.

## Estrutura do projeto

```text
data-challenge-cultivo-inteligente/
  README.md
  requirements.txt
  .gitignore
  data/
  docs/
    Data challenge - Diego Torales e Guilherme Zanini.pdf
    resumo_desenvolvimento.md
    +...
  figures/
    distribuicao_classes.png
    comparacao_modelos.png
    +...
  models/
    .gitkeep
  notebooks/
    00_analise_exploratoria_inicial.ipynb
    01_analise_modelagem_cultivo.ipynb
    +...
  results/
    metadados_modelo.json
    relatorio_classificacao_teste.csv
    +...
```

O modelo treinado e gerado em `models/modelo_cultivo_selecionado.joblib`. Ele nao e versionado por ser um artefato reproduzivel e relativamente volumoso.

## Como executar

### Opção recomendada: Docker

O projeto inclui `Dockerfile` e `docker-compose.yml`, portanto não é necessário instalar as bibliotecas Python diretamente na máquina.

Na raiz deste projeto, execute:

```bash
docker compose up --build -d
```

Aguarde o serviço ficar saudável e confira seu estado:

```bash
docker compose ps
```

Depois, acesse o JupyterLab em [http://localhost:8888](http://localhost:8888). O diretório do projeto é montado em `/workspace`, então as alterações feitas pelo Jupyter aparecem diretamente nos arquivos locais.

Para validar o notebook da Entrega 1 pelo terminal:

```bash
docker compose exec jupyter jupyter nbconvert \
  --to notebook --execute --inplace \
  notebooks/00_analise_exploratoria_inicial.ipynb \
  --ExecutePreprocessor.timeout=900
```

Para encerrar o ambiente:

```bash
docker compose down
```

O JupyterLab está sem token para facilitar o uso local. Não exponha a porta `8888` diretamente na internet.

### Alternativa: ambiente Python local

1. Crie e ative um ambiente virtual.
2. Instale as dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Abra o notebook da Entrega 1:

   ```text
   notebooks/00_analise_exploratoria_inicial.ipynb
   ```

4. Execute as celulas em ordem. O notebook consulta a API do Hugging Face e reproduz a análise exploratória e o experimento inicial descritos no relatório.

O notebook `notebooks/01_analise_modelagem_cultivo.ipynb` permanece disponível como versão mais completa da modelagem.

## Notebooks

| Arquivo | Finalidade |
|---|---|
| `notebooks/00_analise_exploratoria_inicial.ipynb` | Notebook enxuto que acompanha a Entrega 1. Explica a pergunta, aquisição, qualidade, estatísticas, distribuições, correlações, ponto de atenção da umidade, experimento inicial, principais confusões e sensibilidade. |
| `notebooks/01_analise_modelagem_cultivo.ipynb` | Versão completa para continuidade do projeto, com avaliação detalhada, matriz de confusão, importância das variáveis, sensibilidade e exportação de artefatos. |

O notebook da Entrega 1 foi validado dentro do contêiner: 29 células no total, 14 células de código executadas e nenhum erro. Os resultados reproduzem F1 macro médio de `0,9652` na validação cruzada, F1 macro de `0,9725` no teste e a análise de sensibilidade de `0,9680` para `0,9712` para o Random Forest.

## Entregaveis

- notebook executado com exploracao, visualizacoes, metodologia e primeiro experimento;
- sintese da Entrega 1 em Word;
- tabelas de metricas e analise de sensibilidade;
- figuras exportadas para uso no relatorio e na apresentacao;
- modelo preliminar reproduzivel a partir do notebook.

## Proximos passos

1. Confirmar com o professor que o repositorio publico corresponde a base oficial substituta.
2. Documentar origem, unidade e processo de medicao das variaveis.
3. Investigar os registros com umidade acima de 100% sem exclui-los automaticamente.
4. Ajustar hiperparametros usando apenas o conjunto de treino.
5. Avaliar explicacoes por previsao e os erros entre culturas semelhantes.
6. Validar o modelo com dados de solo e clima de uma regiao real antes de qualquer recomendacao pratica.

