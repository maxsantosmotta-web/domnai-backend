# DomnAI — Estado Atual da Execução

Atualizado em: 2026-07-19

## Repositório

- Repositório: `maxsantosmotta-web/domnai-backend`
- Branch principal: `main`
- Ambiente externo ativo: Railway
- Domínio: `https://domnai.iattomassist.com.br`

## Situação geral

- Fase 0: concluída.
- Fase 1 de 8: em execução avançada.
- Fluxo externo atual: backend legado.
- Novo núcleo: isolado, sem montagem na rota principal.

## Concluído e integrado na main

### PR #29 — Fundação isolada

- pacote `app/domnai_core`;
- contratos tipados;
- `ConversationEngine`;
- porta `ModelProvider`;
- validações;
- testes e CI.

Merge principal relacionado: `68b8e3dd74d88ac1a193e72bacfa4b34d3844f75`.

### PR #30 — Capacidades do núcleo

- adaptador OpenAI Responses;
- memória em porta substituível;
- persistência em porta substituível;
- registro de ferramentas;
- rota interna preparada, mas não montada;
- testes e CI.

Merge: `94e69b55b9f16b0c50bcba924f01a0213ad96fae`.

### PR #31 — Anexos e execução controlada

- preparação de imagens e arquivos;
- limites por arquivo, total e quantidade;
- suporte de anexos no adaptador;
- executor de ferramentas;
- limite por turno;
- tratamento de ferramentas inexistentes e retornos inválidos;
- testes e CI.

Merge: `f7bb671e6b72211847a3384c240cdebd612acac9`.

## Em andamento

### PR #32 — Persistência PostgreSQL isolada

- Branch: `feature/source-first-persistence-tool-loop`
- Base inicial: `f7bb671e6b72211847a3384c240cdebd612acac9`
- PR: `#32`
- Estado conhecido no momento deste registro: aberto, aguardando/rodando CI após novas atualizações.

Inclui:
- tabelas exclusivas `domnai_core_memory` e `domnai_core_conversation_records`;
- gerenciador de schema independente;
- `PostgresMemoryStore`;
- `PostgresConversationRepository`;
- serialização segura de solicitações e respostas;
- persistência apenas de metadados de anexos;
- testes com SQLite isolado;
- documentação permanente de roadmap e continuidade.

## Próximo passo exato

1. Verificar a CI do head atual do PR #32.
2. Corrigir somente se houver erro novo comprovado.
3. Integrar o PR #32 se a CI estiver verde.
4. Abrir nova branch a partir da `main` atualizada.
5. Implementar o ciclo controlado modelo → ferramenta → modelo.
6. Adicionar:
   - contrato de solicitação de ferramenta pelo provedor;
   - retorno de resultado ao modelo;
   - limite rígido de iterações;
   - bloqueio de chamadas repetidas;
   - rastreio das etapas;
   - testes unitários.
7. Não registrar ferramentas reais de produção ainda.
8. Não montar a rota interna no `main.py` ainda.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não criar automaticamente as tabelas por importação;
- não ligar a nova memória ao chat externo;
- não remover o backend legado;
- não iniciar testes manuais de conversa antes da arquitetura isolada estar pronta;
- não alterar cobrança, Clerk, Stripe ou regras de créditos.

## Regra de retomada por outra janela

A próxima janela deve:

1. Ler este arquivo inteiro.
2. Ler `docs/DOMNAI_SOURCE_FIRST_ROADMAP.md`.
3. Consultar os PRs e commits mais recentes do repositório.
4. Confirmar o estado real do PR/CI, pois este arquivo pode estar um commit atrás.
5. Retomar do “Próximo passo exato”.
6. Atualizar este arquivo ao concluir cada bloco importante.

## Comando mínimo de retomada

`Continue o DomnAI no repositório maxsantosmotta-web/domnai-backend. Leia primeiro docs/DOMNAI_EXECUTION_STATE.md e docs/DOMNAI_SOURCE_FIRST_ROADMAP.md, confirme PRs e CI atuais e retome exatamente do próximo passo registrado, sem repetir diagnósticos concluídos e sem alterar produção antes da fase correspondente.`
