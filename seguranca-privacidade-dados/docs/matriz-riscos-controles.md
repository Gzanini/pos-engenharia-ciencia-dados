# Matriz de riscos e controles

## Critérios utilizados

- **Confidencialidade:** somente pessoas, processos e sistemas autorizados podem acessar os dados.
- **Integridade:** dados, regras e resultados devem permanecer corretos, completos e rastreáveis.
- **Disponibilidade:** dados e serviços devem estar acessíveis quando necessários.
- **Privacidade:** o tratamento deve respeitar finalidade, necessidade, transparência, não discriminação, retenção e direitos dos titulares.

## Cenário 1 — Plataforma corporativa Data Lakehouse

| Ativo ou etapa | Risco principal | Dimensão afetada | Controles priorizados | Tecnologias aplicáveis |
|---|---|---|---|---|
| Fontes SAP BW, SAP HANA e Salesforce | Extração indevida, conexão comprometida ou coleta excessiva | Confidencialidade e privacidade | Contas de serviço dedicadas, menor privilégio, autenticação forte, minimização e conexões criptografadas | Microsoft Entra ID, Managed Identities, TLS/HTTPS |
| Apache Airflow e pipelines | Credenciais em código ou logs, alteração indevida de DAGs e indisponibilidade | Confidencialidade, integridade e disponibilidade | Cofre de segredos, revisão de código, segregação entre ambientes, controle de mudanças, monitoramento e recuperação | Azure Key Vault, Databricks Secrets, Kubernetes Secrets, Azure Monitor |
| Camada Raw | Exposição de dados em maior granularidade | Confidencialidade e privacidade | Restrição de acesso, classificação, criptografia, mascaramento, retenção e descarte | RBAC, Unity Catalog, criptografia do Azure Storage/ADLS |
| Camadas Silver e Gold | Erros ou adulterações propagados para métricas e produtos | Integridade | Validação de esquema, regras de qualidade, reconciliação, versionamento e linhagem | Delta Lake, Time Travel, Unity Catalog |
| Camada Publish e consumo | Permissões excessivas ou divulgação de informação detalhada | Confidencialidade e privacidade | Acesso por finalidade, segregação de funções, visão agregada, mascaramento e revisão periódica de privilégios | RBAC, Unity Catalog, políticas de acesso do BI |
| Logs, metadados e auditoria | Falta de evidência ou presença de dados sensíveis em logs | Integridade, confidencialidade e responsabilização | Logs centralizados, proteção contra alteração, limitação de conteúdo, alertas e plano de resposta | Databricks Audit Logs, Log Analytics, Microsoft Sentinel |

## Cenário 2 — Concessão de crédito

| Ativo ou etapa | Risco principal | Dimensão afetada | Controles priorizados |
|---|---|---|---|
| Cadastros internos, birôs e Open Finance | Coleta excessiva, fonte não autorizada ou vazamento | Confidencialidade e privacidade | Base legal e finalidade definidas, minimização, autenticação forte, conexão criptografada e controle de acesso |
| Dados de renda, dívidas, patrimônio e histórico | Exposição da situação econômica do titular | Confidencialidade e privacidade | Criptografia, pseudonimização, mascaramento, segregação de ambientes e retenção limitada |
| Motor de decisão e regras | Alteração de regra, erro de processamento ou fraude | Integridade | Gestão de mudanças, validações, versionamento, dupla aprovação e testes |
| Variáveis e modelos analíticos | Discriminação direta ou indireta e decisão injusta | Privacidade, não discriminação e integridade | Revisão de variáveis, testes de viés, monitoramento de desempenho e governança de modelos |
| Decisão de crédito | Falta de explicabilidade ou contestação sem evidências | Transparência e responsabilização | Registro da versão do modelo, variáveis utilizadas, justificativa, canal de revisão e trilha de auditoria |
| Consultas e acessos | Consulta indevida ou ausência de investigação | Confidencialidade e responsabilização | Logs imutáveis, alertas de comportamento anômalo, revisão de acesso e resposta a incidentes |

## Priorização consolidada

1. Classificar os dados e definir responsáveis, finalidade e prazo de retenção.
2. Aplicar autenticação forte, autorização e princípio do menor privilégio.
3. Remover credenciais de códigos e logs e adotar gestão centralizada de segredos.
4. Proteger dados em trânsito e em repouso com criptografia e gestão segura de chaves.
5. Garantir qualidade, versionamento, integridade, linhagem e rastreabilidade.
6. Minimizar, mascarar ou pseudonimizar dados sempre que a identificação direta não for necessária.
7. Centralizar auditoria, monitorar eventos e manter procedimentos de resposta e recuperação.

## Síntese

No Data Lakehouse, o risco central é a propagação de uma falha por camadas e consumidores. Na concessão de crédito, uma falha pode afetar diretamente a vida econômica do titular. Em ambos os casos, a proteção depende da combinação de pessoas, processos e tecnologia durante todo o ciclo de vida dos dados.

