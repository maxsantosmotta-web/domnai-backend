# DomnAI — Roadmap Source-First

Este documento é a referência permanente da reconstrução do núcleo conversacional do DomnAI.

## Objetivo

Substituir o backend conversacional legado por um núcleo source-first, testável, observável e capaz de conversar naturalmente, usar memória, anexos, ferramentas e gerar artefatos sem depender de remendos sobre o fluxo antigo.

## Regra central

O backend legado permanece como fluxo externo ativo até o novo núcleo estar completo, validado em paralelo e pronto para corte controlado.

## Fase 0 — Limpeza e proteção da direção

Status: concluída.

## Fase 1 — Fundação do novo núcleo

Status: concluída.

## Fase 2 — Ferramentas reais e execução multi-etapas

Status: concluída.

PRs principais: #36, #37 e #38.

## Fase 3 — Memória, contexto e identidade conversacional

Status: concluída.

Inclui:
- memória separada por usuário e conversa;
- preferências, decisões, correções, restrições e fatos;
- resumo persistente de históricos longos;
- substituição, conflito e expiração controlados;
- bloqueio de fatos inferidos;
- orientação para uso natural da memória.

PRs principais: #39 e #40.

## Fase 4 — Arquivos, relatórios e artefatos

Status: concluída neste bloco, condicionada à CI verde e integração.

Inclui:
- contrato isolado de artefato com origem `uploaded` ou `generated`;
- armazenamento substituível em memória e PostgreSQL;
- isolamento por proprietário;
- hash SHA-256, tamanho e metadados sem exposição do conteúdo bruto;
- registro seguro de arquivos enviados;
- geração de TXT, Markdown, JSON, CSV, PDF e XLSX;
- leitura textual limitada a formatos autorizados;
- autorização obrigatória por pedido explícito ou aceite contextual confirmado;
- bloqueio de geração binária sem autorização registrada;
- contrato `ArtifactIntent` sem inferência automática por linguagem natural;
- integração opcional por `ArtifactAwareConversationEngine`;
- retenção e expiração controladas;
- recuperação por identificador e filtros;
- visão segura para futura Biblioteca, sem conteúdo bruto;
- arquivos ocultos da Biblioteca quando solicitado;
- testes de segurança, intenção, autorização, geração, leitura, isolamento, persistência, retenção e regressão.

Critério de saída atendido:
- nenhum artefato é gerado sem intenção estruturada e autorização;
- o motor base continua sem efeitos de arquivo quando a integração opcional não é usada;
- arquivos enviados e gerados permanecem separados;
- conteúdo e metadados podem ser persistidos e recuperados com isolamento;
- PDF e XLSX são gerados por bibliotecas próprias e validados;
- expiração impede leitura e listagem após o prazo;
- a futura Biblioteca recebe somente resumos seguros;
- nenhuma rota externa ou fluxo de produção foi alterado.

PRs principais: #41, #42 e bloco de conclusão da Fase 4.

## Fase 5 — API paralela, autenticação e observabilidade

Status: próxima fase; parcialmente preparada, sem montagem externa.

Inclui:
- montar rota paralela protegida;
- autenticação e autorização;
- composição do núcleo completo;
- logs estruturados e correlação;
- métricas externas;
- feature flag e desligamento imediato;
- testes de API sem substituir o fluxo legado.

## Fase 6 — Integração com frontend e validação comparativa

Status: pendente.

## Fase 7 — Corte controlado de produção

Status: pendente.

## Fase 8 — Remoção do legado e estabilização

Status: pendente.

## Regras permanentes de execução

1. Não declarar resolvido por commit ou deploy isolado.
2. Não trocar o fluxo principal antes da validação paralela.
3. Não criar interceptadores ou remendos sobre o legado como solução final.
4. Cada bloco deve ter testes e CI.
5. Mudanças devem ser pequenas o suficiente para rollback, mas agrupadas quando independentes e seguras.
6. Produção, frontend, cobrança e autenticação só mudam na fase correspondente.
7. Atualizar `docs/DOMNAI_EXECUTION_STATE.md` ao final de cada bloco relevante.
