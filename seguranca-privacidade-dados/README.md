# Segurança e Privacidade de Dados

Trabalho acadêmico da disciplina de Segurança e Privacidade de Dados da pós-graduação em Engenharia e Ciência de Dados da Unisinos.

## Integrantes

- Diego Arruda Torales
- Guilherme Zanini da Silva

## Tema

Análise de segurança da informação e privacidade em dois cenários reais de uso intensivo de dados:

1. uma plataforma corporativa Data Lakehouse;
2. um processo de concessão de crédito.

O estudo diferencia segurança da informação de privacidade e mostra como os dois temas se complementam durante todo o ciclo de vida dos dados. A segurança é analisada principalmente pelos pilares de confidencialidade, integridade e disponibilidade; a privacidade considera finalidade, necessidade, não discriminação, minimização, retenção e descarte.

## Objetivos

- identificar os dados e ativos que exigem proteção;
- analisar ameaças, vulnerabilidades e impactos de incidentes;
- relacionar riscos aos princípios da LGPD;
- priorizar controles técnicos, organizacionais e jurídicos;
- demonstrar que criptografia isolada não é suficiente;
- aplicar os conceitos de Privacy by Design e defesa em profundidade.

## Cenários analisados

### Plataforma corporativa Data Lakehouse

O fluxo integra dados provenientes de SAP BW, SAP HANA e Salesforce. A orquestração é realizada por pipelines do Apache Airflow e o processamento ocorre em uma arquitetura Data Lakehouse organizada nas camadas Raw, Silver, Gold e Publish.

Os principais riscos são:

- exposição de dados na camada Raw;
- propagação de erros ou adulterações entre camadas;
- permissões excessivas na camada de consumo;
- credenciais ou segredos expostos em código e logs;
- indisponibilidade de pipelines e serviços dependentes;
- ausência de rastreabilidade sobre transformações e acessos.

Controles priorizados:

- classificação da informação e controle de acesso por responsabilidade e camada;
- princípio do menor privilégio e segregação de funções;
- proteção de credenciais em cofres de segredos;
- criptografia em trânsito e em repouso;
- validação, versionamento, integridade e linhagem dos dados;
- auditoria, monitoramento, resposta e recuperação de incidentes;
- minimização, mascaramento, pseudonimização, retenção e descarte.

Tecnologias aplicáveis incluem Microsoft Entra ID, RBAC, Azure Key Vault, Managed Identities, Databricks Secrets, TLS/HTTPS, Delta Lake, Unity Catalog, Databricks Audit Logs, Azure Monitor, Log Analytics e Microsoft Sentinel. Elas são apresentadas como alternativas técnicas compatíveis com o cenário, não como evidência de implantação em uma organização específica.

### Concessão de crédito

O processo utiliza dados de cadastros internos, birôs de crédito e Open Finance para apoiar decisões de aprovação, recusa ou ajuste das condições de crédito.

Os principais riscos são:

- fraude financeira;
- exposição indevida da situação econômica do proponente;
- decisões incorretas causadas por dados alterados ou de baixa qualidade;
- discriminação direta ou indireta por variáveis e modelos;
- sanções regulatórias e dano reputacional;
- falta de explicabilidade e rastreabilidade da decisão.

Controles priorizados:

- autenticação, autorização e menor privilégio;
- criptografia forte e gestão segura de chaves;
- proteção de dados em trânsito, em processamento e em repouso;
- anonimização ou pseudonimização em ambientes analíticos;
- logs imutáveis e rastreabilidade das decisões;
- aplicação dos princípios de finalidade, necessidade e não discriminação.

## Estrutura da pasta

```text
seguranca-privacidade-dados/
├── README.md
└── docs/
    ├── README.md
    ├── analise-seguranca-privacidade.pdf
    ├── apresentacao-seguranca-privacidade.pdf
    └── matriz-riscos-controles.md
```

## Entregáveis

- [Artigo — análise de segurança e privacidade](docs/analise-seguranca-privacidade.pdf)
- [Apresentação](docs/apresentacao-seguranca-privacidade.pdf)
- [Matriz de riscos e controles](docs/matriz-riscos-controles.md)
- [Índice da documentação](docs/README.md)

## Resultado principal

Os dois cenários exigem controles combinados ao longo de todo o ciclo de vida dos dados. Classificação, menor privilégio, minimização, segregação, criptografia, rastreabilidade, auditoria e resposta a incidentes formam uma proteção mais consistente do que qualquer mecanismo aplicado isoladamente.

## Observações

- Os documentos finais foram preservados no formato entregue.
- O repositório não contém dados pessoais, credenciais ou segredos dos ambientes analisados.
- A arquitetura representa um cenário de estudo e não documenta configurações internas de uma organização real.
- As tecnologias citadas são exemplos aplicáveis aos controles propostos.

