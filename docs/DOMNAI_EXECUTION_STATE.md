# DomnAI — Estado Atual da Execução

Atualizado em: 2026-07-19

## Repositório

- Repositório: `maxsantosmotta-web/domnai-backend`
- Branch principal: `main`
- Ambiente externo ativo: Railway
- Domínio: `https://domnai.iattomassist.com.br`

## Situação geral

- Fase 0: concluída.
- Fase 1 de 8: concluída.
- Fase 2 de 8: em execução.
- Fluxo externo atual: backend legado.
- Novo núcleo: isolado, sem montagem na rota principal.

## Concluído e integrado na main

### Fundação e capacidades do núcleo

- PR #29: pacote isolado, contratos tipados e `ConversationEngine`.
- PR #30: adaptador OpenAI Responses, portas de memória/persistência e rota interna preparada.
- PR #31: anexos e execução controlada.
- PR #32: persistência PostgreSQL isolada.
- PR #33: ciclo controlado modelo → ferramenta → modelo.
- PR #34: ferramentas nativas da Responses API e continuidade por `call_id`.
- PR #35: configuração, composição, observabilidade e rota interna executável ainda não montada.

Merge mais recente antes do PR #36: `15be13ad50eb839ff536032f3754e8b27e4ea8d3`.

## PR #36 — início operacional da Fase 2

Branch: `feature/source-first-phase2-real-tools`

Estado validado:
- CI `Backend unit tests #489`: concluída com sucesso;
- regressões do núcleo anterior: aprovadas;
- testes novos da Fase 2: aprovados;
- pronto para integração na `main`.

Inclui:
- ferramenta real `calculate_expression`, com avaliação aritmética por AST e sem execução de código;
- ferramenta real `analyze_text`, com contagens determinísticas;
- limites de tamanho, potência e resultado;
- ativação por `DOMNAI_CORE_ENABLE_BUILTIN_TOOLS`;
- composição automática e explicitamente substituível do registro;
- falhas de ferramenta devolvidas ao modelo como resultado estruturado e recuperável;
- preservação de `call_id` e histórico de cada execução;
- contagem de falhas recuperáveis no resultado final;
- preservação do contrato anterior para ferramentas bem-sucedidas;
- testes de segurança, resultado e recuperação;
- CI detalhada por capacidade;
- roadmap atualizado com Fase 1 concluída e Fase 2 iniciada.

## Próximo passo exato

1. Confirmar que o PR #36 foi integrado na `main`.
2. Abrir nova branch a partir da `main` atualizada.
3. Continuar a Fase 2 com um bloco agrupado contendo:
   - política de risco por ferramenta;
   - timeout e limites específicos;
   - rastreio estruturado de execução;
   - fluxo multi-etapas determinístico com mais de uma ferramenta;
   - testes de falha, limite e compatibilidade.
4. Não montar a rota interna no `main.py` ainda.
5. Não alterar frontend nem tráfego de produção.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não ligar a nova memória ao chat externo;
- não registrar ferramentas com efeitos externos sem política e autorização;
- não remover o backend legado;
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
