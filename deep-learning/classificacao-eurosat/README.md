# Deep Learning - Classificacao de uso e cobertura do solo com EuroSAT

Projeto pratico da disciplina `2026/2 - Deep Learning - LT96012-00004-1000004`.

O trabalho compara duas familias de redes neurais convolucionais para classificar imagens de satelite do EuroSAT RGB:

1. uma CNN construida e treinada do zero;
2. uma ResNet50 pre-treinada no ImageNet, adaptada por transfer learning e fine-tuning.

## Pergunta do projeto

**Em que medida uma CNN treinada do zero e uma ResNet50 pre-treinada conseguem distinguir as dez classes do EuroSAT, e como diferentes hiperparametros afetam o desempenho e a generalizacao?**

## Dataset

O EuroSAT RGB possui 27.000 imagens de 64 x 64 pixels obtidas pelo satelite Sentinel-2. As amostras pertencem a dez classes de uso e cobertura do solo:

- AnnualCrop;
- Forest;
- HerbaceousVegetation;
- Highway;
- Industrial;
- Pasture;
- PermanentCrop;
- Residential;
- River;
- SeaLake.

O notebook baixa o arquivo RGB oficial do Zenodo para o cache local do Keras e cria divisões estratificadas e reproduzíveis. A fonte original e o artigo do dataset permanecem citados no relatório; os dados não são gravados no repositório.

## Metodologia

1. Aquisicao e verificacao das imagens.
2. Analise da distribuicao das classes e inspecao visual.
3. Separacao deterministica em treino (70%), validacao (15%) e teste (15%).
4. Data augmentation compativel com imagens de satelite.
5. Comparacao de configuracoes da CNN do zero.
6. Comparacao de cabecas e estrategias de ajuste da ResNet50.
7. Selecao pela metrica F1 macro no conjunto de validacao.
8. Avaliacao unica dos modelos selecionados no teste reservado.
9. Analise de matriz de confusao, metricas por classe e exemplos de erro.

## Estrutura

```text
classificacao-eurosat/
  Dockerfile
  docker-compose.yml
  .dockerignore
  README.md
  requirements.txt
  notebooks/
    classificacao_eurosat.ipynb
  figures/
  results/
  models/
  scripts/
    build_notebook.py
    docker_notebook.ps1
    enrich_notebook.py
```

Os arquivos em `figures/`, `results/` e `models/` sao gerados pelo notebook. Modelos treinados nao sao versionados por serem artefatos reproduziveis e potencialmente grandes.

O script `scripts/enrich_notebook.py` incorpora as figuras geradas e a discussão final no próprio `.ipynb`. Ele deve ser executado somente depois da execução completa dos experimentos.

## Execucao alternativa no Google Colab

1. Abra `notebooks/classificacao_eurosat.ipynb` no Google Colab.
2. Ative uma GPU em `Ambiente de execucao > Alterar tipo de ambiente de execucao`.
3. Execute todas as celulas em ordem.
4. Para a entrega final, mantenha `EXECUTAR_EXPERIMENTOS = True` e salve o notebook com todas as saidas.

O download inicial e os experimentos completos podem levar alguns minutos. O tempo depende da disponibilidade de GPU do Colab.

## Execucao recomendada com Docker e RTX 3060

O notebook não seleciona o sistema operacional ou a GPU por conta própria. Ele usa o ambiente associado ao kernel Jupyter. A configuração Docker deste projeto executa Jupyter Lab em Linux, com TensorFlow 2.20 e acesso explícito à GPU NVIDIA.

Pré-requisitos:

- Docker Desktop usando o backend WSL 2;
- drivers NVIDIA atualizados;
- suporte a containers GPU habilitado no Docker Desktop.

Para construir a imagem, iniciar o container e validar a GPU:

```powershell
cd "C:\Users\Guilherme_Zanini\Documents\github\pos-engenharia-ciencia-dados\deep-learning\classificacao-eurosat"
.\scripts\docker_notebook.ps1 start
```

Depois, abrir:

```text
http://localhost:8888/lab?token=eurosat
```

No Jupyter Lab, abrir `notebooks/classificacao_eurosat.ipynb` e executar `Run > Run All Cells`. A primeira célula de ambiente deve listar uma GPU física NVIDIA.

Comandos auxiliares:

```powershell
# Verificar container
.\scripts\docker_notebook.ps1 status

# Verificar RTX dentro do container
.\scripts\docker_notebook.ps1 gpu

# Acompanhar logs
.\scripts\docker_notebook.ps1 logs

# Encerrar sem apagar o cache do dataset
.\scripts\docker_notebook.ps1 stop
```

O diretório do projeto é montado em `/workspace`. O download do EuroSAT é armazenado no volume Docker `eurosat_keras_cache`, fora do Git, e é reutilizado nas próximas execuções.

O primeiro build baixa as bibliotecas do TensorFlow, CUDA e cuDNN e, por isso, é mais demorado. As inicializações seguintes reutilizam a imagem pronta. A configuração foi validada com TensorFlow 2.20, Linux, Docker Desktop/WSL 2 e uma RTX 3060; uma operação matricial de teste foi efetivamente alocada em `/device:GPU:0`.

Os resultados já incorporados ao notebook foram produzidos anteriormente no Linux via WSL, com TensorFlow 2.13.1 e a mesma RTX 3060. O Docker foi acrescentado e validado como ambiente reproduzível para novas execuções. Uma nova execução completa no Docker pode produzir pequenas variações numéricas devido à mudança da versão do TensorFlow, apesar das sementes fixadas.

## Execucao local sem Docker

Recomenda-se Python 3.11. No Windows nativo, TensorFlow 2.20 normalmente executará em CPU; para utilizar a GPU, prefira o Docker configurado acima ou um ambiente Linux/WSL corretamente preparado.

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 -m jupyter notebook notebooks/classificacao_eurosat.ipynb
```

## Criterio de selecao

As configuracoes sao comparadas apenas na validacao. O F1 macro e usado como criterio principal porque atribui o mesmo peso a cada classe. O teste permanece reservado ate a escolha da melhor configuracao de cada familia.

## Resultados obtidos

| Família | Modelo selecionado | Acurácia no teste | F1 macro no teste |
|---|---:|---:|---:|
| CNN treinada do zero | CNN-2 | 81,93% | 81,22% |
| Transfer learning | TL-3 | **96,10%** | **95,98%** |

A CNN-2 combina quatro blocos convolucionais, Batch Normalization, regularização L2, dropout e RMSprop. No transfer learning, o melhor resultado foi obtido ao continuar a TL-1 com fine-tuning das 30 últimas camadas da ResNet50 e taxa de aprendizado de `1e-5`.

O ganho de 14,76 pontos percentuais de F1 macro da TL-3 sobre a CNN-2 mostra a vantagem das representações pré-treinadas para este conjunto. A classe com menor F1 na TL-3 foi `PermanentCrop` (93,69%), enquanto `SeaLake` alcançou 98,99%. Os valores completos e as matrizes de confusão estão em `results/` e `figures/`.

Todas as figuras também estão incorporadas diretamente no notebook, seguindo o padrão dos notebooks da disciplina. A discussão relaciona profundidade, ativação, regularização, função de erro, otimizador e fine-tuning aos resultados de validação, sem interpretar comparações multifatoriais como causalidade isolada.

## Limitacoes

- O experimento utiliza apenas as bandas RGB, nao as 13 bandas originais do Sentinel-2.
- A separacao aleatoria mede generalizacao interna, mas nao substitui validacao geografica em regioes totalmente novas.
- Imagens espacialmente proximas podem compartilhar caracteristicas, elevando as metricas em relacao a uma divisao por localidade.
- O modelo identifica padroes visuais das classes do dataset; ele nao deve ser interpretado como sistema operacional de monitoramento territorial sem validacao externa.

## Entregaveis

- notebook executado em estilo literate programming;
- tabelas de todos os experimentos;
- curvas de aprendizado e matrizes de confusao;
- relatorios de classificacao e metricas finais;

