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

Status: concluída neste bloco, condicionada à CI verde e integração.

Inclui:
- memória separada por usuário e conversa;
- composição de contexto durável e específico;
- preferências, decisões, correções, restrições e fatos;
- fatos aceitos apenas quando informados pelo usuário;
- deduplicação e limites por categoria;
- resumo controlado e persistente de históricos longos;
- substituição por chave para informação mais recente;
- correções recentes removendo informações conflitantes antigas;
- expiração opcional por item;
- poda automática de memória expirada;
- orientação ao provedor para uso natural e discreto da memória;
- instrução explícita para não transformar inferências em fatos;
- reconhecimento de incerteza em caso de conflito;
- compatibilidade com a memória anterior quando não há escopo de usuário;
- testes de continuidade, conflito, expiração, resumo e regressão.

Critério de saída atendido:
- memória possui escopo claro por usuário e conversa;
- correções recentes prevalecem sobre registros conflitantes;
- resumos longos sobrevivem entre turnos;
- dados temporários podem expirar sem intervenção manual;
- fatos não são persistidos a partir de inferências do modelo;
- o provedor recebe orientação para usar memória sem comportamento robótico;
- fases anteriores continuam cobertas pela CI.

PRs principais: #39 e bloco de conclusão da Fase 3.

## Fase 4 — Arquivos, relatórios e artefatos

Status: próxima fase.

Inclui:
- leitura segura de anexos;
- PDF, XLSX, CSV e outros artefatos sob pedido;
- armazenamento e recuperação;
- integração com Biblioteca;
- separação entre arquivos enviados e arquivos gerados;
- validação de conteúdo e limites.

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
