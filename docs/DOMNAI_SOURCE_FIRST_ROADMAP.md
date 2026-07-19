# DomnAI — Roadmap Source-First

Este documento é a referência permanente da reconstrução do núcleo conversacional do DomnAI.

## Objetivo

Substituir o backend conversacional legado por um núcleo source-first, testável, observável e capaz de conversar naturalmente, usar memória, anexos, ferramentas e gerar artefatos sem depender de remendos sobre o fluxo antigo.

## Regra central

O backend legado permanece como fluxo externo ativo até o novo núcleo estar completo, validado em paralelo e pronto para corte controlado.

## Fase 0 — Limpeza e proteção da direção

Status: concluída.

Inclui:
- proteção do chat livre por padrão;
- operação tratada como contexto, não roteiro obrigatório;
- despedida contextual;
- geração de PDF/planilha somente por pedido explícito ou aceite contextual real;
- testes de regressão da direção source-first.

PRs principais: #26, #27 e #28.

## Fase 1 — Fundação do novo núcleo

Status: em execução avançada.

Inclui:
- pacote isolado `app/domnai_core`;
- contratos tipados;
- `ConversationEngine`;
- porta de provedor;
- adaptador OpenAI Responses;
- memória e persistência por portas substituíveis;
- registro e executor de ferramentas;
- anexos;
- rota interna de prévia ainda não montada;
- persistência PostgreSQL exclusiva do novo núcleo;
- ciclo controlado modelo → ferramenta → modelo.

PRs principais: #29, #30, #31 e #32.

Critério de saída:
- núcleo isolado completo;
- testes unitários cobrindo contratos, memória, anexos, persistência e ferramentas;
- nenhum acoplamento obrigatório ao backend legado.

## Fase 2 — Ferramentas reais e execução multi-etapas

Status: pendente.

Inclui:
- contrato oficial de chamadas de ferramentas vindas do modelo;
- ferramentas reais registradas explicitamente;
- limite de iterações;
- proteção contra repetição e loops;
- rastreio de cada etapa;
- falhas previsíveis e recuperáveis.

## Fase 3 — Memória, contexto e identidade conversacional

Status: pendente.

Inclui:
- memória persistente com escopo por usuário e conversa;
- resumo de contexto longo;
- preferências, decisões, correções e restrições;
- prevenção de fatos inventados pela própria IA;
- comportamento natural e contextual do DomnAI.

## Fase 4 — Arquivos, relatórios e artefatos

Status: pendente.

Inclui:
- leitura segura de anexos;
- PDF, XLSX, CSV e outros artefatos sob pedido;
- armazenamento e recuperação;
- integração com Biblioteca;
- separação entre arquivos enviados e arquivos gerados;
- validação de conteúdo e limites.

## Fase 5 — API paralela, autenticação e observabilidade

Status: pendente.

Inclui:
- montar rota paralela protegida;
- autenticação e autorização;
- métricas de latência, tokens, ferramentas e falhas;
- logs estruturados;
- correlação por conversa;
- feature flags e desligamento imediato.

## Fase 6 — Integração com frontend e validação comparativa

Status: pendente.

Inclui:
- frontend apontando opcionalmente para o novo núcleo;
- usuários internos ou tráfego controlado;
- comparação com o fluxo legado;
- testes reais de conversa, memória, anexos, ferramentas e arquivos;
- correção de divergências antes do corte.

## Fase 7 — Corte controlado de produção

Status: pendente.

Inclui:
- migração gradual do tráfego;
- monitoramento em produção;
- rollback simples;
- validação do domínio Railway;
- confirmação de que o novo núcleo é o fluxo principal.

## Fase 8 — Remoção do legado e estabilização

Status: pendente.

Inclui:
- remoção dos caminhos antigos somente após estabilidade comprovada;
- limpeza de código e scripts de build;
- documentação operacional final;
- testes de regressão completos;
- encerramento da migração.

## Regras permanentes de execução

1. Não declarar resolvido por commit ou deploy isolado.
2. Não trocar o fluxo principal antes da validação paralela.
3. Não criar interceptadores ou remendos sobre o legado como solução final.
4. Cada bloco deve ter testes e CI.
5. Mudanças devem ser pequenas o suficiente para rollback, mas agrupadas quando independentes e seguras.
6. Produção, frontend, cobrança e autenticação só mudam na fase correspondente.
7. Atualizar `docs/DOMNAI_EXECUTION_STATE.md` ao final de cada bloco relevante.
