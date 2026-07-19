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
- Fase 2 de 8: em execução avançada.
- Fluxo externo atual: backend legado.
- Novo núcleo: isolado, sem montagem na rota principal.

## Concluído e integrado na main

- PR #29: pacote isolado, contratos tipados e `ConversationEngine`.
- PR #30: adaptador OpenAI Responses, portas de memória/persistência e rota interna preparada.
- PR #31: anexos e execução controlada.
- PR #32: persistência PostgreSQL isolada.
- PR #33: ciclo controlado modelo → ferramenta → modelo.
- PR #34: ferramentas nativas da Responses API e continuidade por `call_id`.
- PR #35: configuração, composição, observabilidade e rota interna executável ainda não montada.
- PR #36: ferramentas reais locais, falhas recuperáveis e início operacional da Fase 2.

Merge mais recente antes deste bloco: `75afb7f27b5951cae4922c080526fe4e5243016e`.

## Bloco atual — políticas, timeout e execução multi-etapas

Branch: `feature/source-first-phase2-policy-timeouts`

Inclui:
- política individual por ferramenta com risco `low`, `medium` ou `high`;
- autorização global dos níveis permitidos;
- timeout específico por ferramenta;
- limite individual de chamadas por turno;
- limite global de chamadas por turno;
- rastreio estruturado com sequência, iteração, duração, risco, status e `call_id`;
- falhas de política e timeout devolvidas ao modelo como resultado recuperável;
- preservação do formato anterior de resultados bem-sucedidos;
- fluxo determinístico com duas ferramentas diferentes no mesmo turno;
- endpoint interno de status com riscos e limites configurados;
- testes de política, timeout, limites, compatibilidade e multi-etapas;
- CI detalhada atualizada.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir qualquer regressão sem retirar cobertura ou compatibilidade.
4. Integrar somente com CI verde.
5. Continuar a Fase 2 com um bloco agrupado contendo:
   - ferramentas seguras de leitura e transformação sem efeitos externos;
   - correlação por conversa e solicitação;
   - catálogo e descrição operacional das ferramentas;
   - fluxos multi-etapas mais longos;
   - critério formal de encerramento da Fase 2.
6. Não montar a rota interna no `main.py` ainda.
7. Não alterar frontend nem tráfego de produção.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não ligar a nova memória ao chat externo;
- não registrar ferramentas com efeitos externos sem autorização específica;
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
