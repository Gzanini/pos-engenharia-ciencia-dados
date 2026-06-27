# Pré-processamento de Dados - Vendas

Projeto prático da disciplina com foco em um pipeline de pré-processamento aplicado a dados de vendas.

## Proposta
- Problema de negócio: entender desempenho de vendas, mix de produtos e comportamento das movimentações.
- Objetivo: unir os dados brutos, diagnosticar qualidade, limpar inconsistências e gerar uma base analítica confiável.

## Fontes de dados
- `dados/raw/movimentacoes_20260501.json` a `dados/raw/movimentacoes_20260512.json`
- `dados/raw/produtos_servicos_20260512.csv`

## Estrutura
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
  notebooks/
    01_projeto_pratico_vendas.ipynb
  README.md
```

## Como executar
1. Suba o ambiente:
   ```bash
   docker compose up --build -d
   ```
2. Acesse o Jupyter:
   - `http://localhost:8888`
   - token: `python@2026`
3. Abra o notebook principal em `notebooks/01_projeto_pratico_vendas.ipynb`

## Configuracao do .env
Crie um arquivo `.env` na raiz desta pasta com o seguinte conteudo:

```env
JUPYTER_PORT=8888
JUPYTER_TOKEN=python@2026
```

## Entregáveis previstos
- Notebook com relatório final e código comentado
- Arquivo `grupo.txt`
- Vídeo curto apresentando o problema, o pipeline e os resultados

## Padrão de desenvolvimento
- Separar `raw` e `processed`
- Usar notebook com narrativa de negócio
- Reutilizar o mesmo estilo de container do outro projeto da pós
