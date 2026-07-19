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

Status: em execução.

Já implementado:
- contrato isolado de artefato com origem `uploaded` ou `generated`;
- armazenamento substituível por porta própria;
- implementação em memória para desenvolvimento e testes;
- isolamento por proprietário;
- hash SHA-256, tamanho e metadados sem exposição do conteúdo bruto;
- registro seguro de arquivos enviados;
- geração determinística de TXT, Markdown, JSON e CSV;
- leitura textual limitada a formatos explicitamente autorizados;
- persistência PostgreSQL isolada de conteúdo e metadados;
- geração real de PDF com ReportLab;
- geração real de XLSX com openpyxl;
- autorização obrigatória por pedido explícito ou aceite contextual confirmado;
- bloqueio de registro binário sem autorização registrada;
- recuperação por identificador e filtros por proprietário/origem;
- expiração opcional com ocultação em leitura e listagem;
- testes de segurança, autorização, geração, leitura, isolamento, persistência e regressão.

Próximo escopo:
- integração controlada do fluxo de artefatos ao `ConversationEngine`;
- contrato de intenção para impedir geração automática indevida;
- retenção, recuperação e preparação da futura Biblioteca;
- entrega segura sem exposição do conteúdo bruto;
- critério formal de saída da Fase 4.

## Fase 5 — API paralela, autenticação e observabilidade

Status: parcialmente preparada, sem montagem externa.

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
