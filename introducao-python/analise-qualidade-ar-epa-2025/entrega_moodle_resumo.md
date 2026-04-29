# Entrega - Análise Exploratória da Qualidade do Ar (Moodle)

## Contexto da atividade
- Desenvolver uma análise e visualização de dados com Python usando dados públicos da EPA.
- Base de dados: **Daily Summary Data** (EPA), para um ano específico.
- Cidade escolhida no trabalho: **New York** (ano 2025).

## O que precisa ser entregue
- Um arquivo **IPython Notebook (.ipynb)** contendo todo o código.
- Notebook deve estar:
  - estruturado por seções
  - bem comentado
  - com nomes de variáveis claros
  - com análise e conclusão documentadas

## Itens obrigatórios no notebook
1. **Configuração do ambiente**
- Uso de Python/Jupyter (IDE configurada).
- Bibliotecas necessárias instaladas: `pandas`, `numpy`, `matplotlib`, `seaborn`.

2. **Carregamento e tratamento dos dados**
- Carregar os dados com `pandas` em DataFrame.
- Fazer limpeza inicial dos dados.
- Tratar/remover valores faltantes.
- Corrigir tipos de dados quando necessário.

3. **Exploração e análise dos dados**
- Mostrar primeiras linhas da base (`head`).
- Verificar tipos de dados e estrutura (`info`, `shape`).
- Explorar estatísticas básicas (`describe` e medidas principais).
- Realizar análise estatística descritiva com foco em:
  - média
  - mediana
  - desvio padrão
  - quartis

4. **Visualização de dados**
- Criar gráficos com `matplotlib`/`seaborn`.
- Incluir visualizações que mostrem tendências ao longo do tempo e análises relevantes.
- Garantir títulos e rótulos dos eixos.

5. **Interpretação e conclusão**
- Interpretar os gráficos e os resultados numéricos.
- Apresentar conclusões sobre padrões/tendências observados.
- Documentar observações de forma clara e concisa.

## Critérios de avaliação (resumo)
- Qualidade e organização do script.
- Eficácia no uso do `pandas` para limpeza/tratamento.
- Exploração e análise estatística correta.
- Qualidade e relevância das visualizações.
- Clareza da interpretação e da documentação final.

## Checklist rápido antes de enviar
- [ ] Notebook `.ipynb` abre e executa sem erro.
- [ ] Todas as células principais estão executadas (com saídas visíveis).
- [ ] Gráficos aparecem corretamente.
- [ ] Interpretação e conclusão estão preenchidas.
- [ ] Arquivo final está organizado e comentado.

## Observação
- Conforme alinhamento com o professor, **não é obrigatório comparar com outra base** para esta entrega.
