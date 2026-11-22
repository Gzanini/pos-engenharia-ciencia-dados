# Data Challenge - Recomendação de Cultivo Inteligente

Projeto da disciplina `2026/2 - Data Challenge - LT96012-00004-1000006`.

O trabalho desenvolve um classificador multiclasse para recomendar uma cultura agrícola a partir de atributos do solo e do microclima. A recomendação representa compatibilidade com os padrões observados na base de treinamento. O resultado não substitui validação agronômica nem permite estimar produtividade ou retorno financeiro.

## Problema do projeto

A pergunta central:

**Em que medida os teores de nitrogênio, fósforo e potássio, combinados com temperatura, umidade, pH e precipitação, permitem identificar a cultura mais compatível entre as 22 classes da base?**

## Fonte de dados

O notebook consulta a API do Hugging Face para localizar o arquivo publicado no dataset [`randalakab/Crop-recommendation`](https://huggingface.co/datasets/randalakab/Crop-recommendation).

O grupo realizou a aquisição e a análise da base pública, não a coleta original das medições agrícolas. A fonte consultada não documenta de forma suficiente a região, o período, o método de coleta e as unidades de todas as variáveis.

A base analisada possui:

- 2.200 registros;
- sete variáveis preditoras;
- 22 culturas, com 100 observações por classe;
- nenhum valor ausente;
- nenhuma linha duplicada;
- 19 registros com umidade acima de 100%.

## Metodologia

1. Inspeção do esquema, tipos, valores ausentes, duplicidades e extremos.
2. Análise descritiva e visual das variáveis.
3. Separação estratificada de 80% para treino e 20% para teste.
4. Comparação de baseline, regressão logística, árvore de decisão e Random Forest.
5. Validação cruzada estratificada com cinco partições apenas no conjunto de treino.
6. Seleção do modelo pelo F1 macro médio.
7. Avaliação final no conjunto de teste reservado.
8. Análise de sensibilidade para os registros com umidade acima de 100%.

## Resultados da Entrega 1

| Modelo | F1 macro médio na validação cruzada | Desvio-padrão |
|---|---:|---:|
| Random Forest | 0,9652 | 0,0069 |
| Regressão logística | 0,9254 | 0,0108 |
| Árvore de decisão | 0,9096 | 0,0067 |
| Baseline | 0,0040 | 0,0000 |

O Random Forest foi selecionado. No conjunto de teste reservado, obteve acurácia de 0,9727 e F1 macro de 0,9725. Foram 12 classificações incorretas em 440 observações. A confusão mais frequente ocorreu entre `kidneybeans` e `chickpea`.

Essas métricas são preliminares e medem o desempenho interno nesta base. Como o dataset não informa local, data, método de coleta ou unidade documentada de todas as variáveis, o resultado não demonstra generalização para uma região agrícola real.

## Solução e validação final

A Entrega 2 amplia o experimento inicial sem alterar os artefatos da Entrega 1. O novo notebook compara cinco famílias de modelos, ajusta o Extra Trees somente no conjunto de treino e realiza uma única avaliação final no teste reservado.

| Indicador final | Resultado |
|---|---:|
| F1 macro no teste | 0,9750 |
| Acurácia no teste | 0,9750 |
| Top-3 accuracy | 1,0000 |
| Log loss | 0,1797 |
| Erros | 11 de 440 |

O modelo final utiliza 900 árvores, profundidade máxima 20, `max_features=0.75` e `min_samples_split=8`. A importância por permutação apontou umidade, nitrogênio e precipitação como os atributos de maior impacto preditivo. Isso descreve o comportamento do classificador, não causalidade agronômica.

A saída operacional retorna as três culturas mais compatíveis e alerta quando algum atributo está fora das faixas observadas no treino. O uso proposto continua sendo experimental e supervisionado: dados regionais, produtividade, custos e validação agronômica ainda são necessários antes de uma decisão real de plantio.

## Estrutura do projeto

```text
data-challenge-cultivo-inteligente/
  README.md
  requirements.txt
  .gitignore
  docs/
    Data challenge - Diego Torales e Guilherme Zanini.pdf
    Data challenge E2 - Diego Torales e Guilherme Zanini.pdf
    Apresentação Data challenge - Diego Torales e Guilherme Zanini.pdf
  figures/
    distribuicao_classes.png
    comparacao_modelos.png
    +...
  models/
    .gitkeep
  notebooks/
    00_analise_exploratoria_inicial.ipynb
    01_analise_modelagem_cultivo.ipynb
    02_solucao_validacao_final.ipynb
    +...
  results/
    metadados_modelo.json
    relatorio_classificacao_teste.csv
    +...
```

O modelo treinado é gerado em `models/modelo_cultivo_selecionado.joblib`. Ele não é versionado por ser um artefato reproduzível e relativamente volumoso.

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

Para reproduzir a Entrega 2:

```bash
docker compose exec jupyter jupyter nbconvert \
  --to notebook --execute --inplace \
  notebooks/02_solucao_validacao_final.ipynb \
  --ExecutePreprocessor.timeout=1800
```

Para gerar uma versão HTML com todas as células e resultados:

```bash
docker compose exec jupyter jupyter nbconvert \
  --to html notebooks/02_solucao_validacao_final.ipynb \
  --output 02_solucao_validacao_final \
  --output-dir results
```

Para encerrar o ambiente:

```bash
docker compose down
```

### Alternativa: ambiente Python local

1. Crie e ative um ambiente virtual.
2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Abra o notebook da Entrega 1:

   ```text
   notebooks/00_analise_exploratoria_inicial.ipynb
   ```

4. Execute as células em ordem. O notebook consulta a API do Hugging Face e reproduz a análise exploratória e o experimento inicial descritos no relatório.

O notebook `notebooks/01_analise_modelagem_cultivo.ipynb` permanece disponível como versão mais completa da modelagem.

## Notebooks

| Arquivo | Finalidade |
|---|---|
| `notebooks/00_analise_exploratoria_inicial.ipynb` | Notebook enxuto que acompanha a Entrega 1. Explica a pergunta, aquisição, qualidade, estatísticas, distribuições, correlações, ponto de atenção da umidade, experimento inicial, principais confusões e sensibilidade. |
| `notebooks/01_analise_modelagem_cultivo.ipynb` | Versão completa para continuidade do projeto, com avaliação detalhada, matriz de confusão, importância das variáveis, sensibilidade e exportação de artefatos. |
| `notebooks/02_solucao_validacao_final.ipynb` | Entrega 2: pipeline final, comparação de cinco modelos, ajuste controlado, curva de aprendizado, teste reservado, erros, confiança, importância por permutação, sensibilidade e protótipo top 3. |

O notebook da Entrega 1 foi validado dentro do contêiner: 29 células no total, 14 células de código executadas e nenhum erro. Os resultados reproduzem F1 macro médio de `0,9652` na validação cruzada, F1 macro de `0,9725` no teste e a análise de sensibilidade de `0,9680` para `0,9712` para o Random Forest.

## Entregáveis

- notebook executado com exploração, visualizações, metodologia e primeiro experimento;
- tabelas de métricas e análise de sensibilidade;
- figuras exportadas para uso no relatório e na apresentação;
- modelo preliminar reproduzível a partir do notebook;
- notebook final executado e exportação HTML;
- relatório final e apresentação em PDF;
- tabelas, figuras e metadados reproduzíveis da Entrega 2.

