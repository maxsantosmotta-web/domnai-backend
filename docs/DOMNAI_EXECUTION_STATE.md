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
- Fase 2 de 8: concluída neste bloco, condicionada à CI verde e merge.
- Próxima fase: Fase 3 — memória, contexto e identidade conversacional.
- Fluxo externo atual: backend legado.
- Novo núcleo: isolado, sem montagem na rota principal.

## Concluído e integrado na main antes deste bloco

- PR #29: pacote isolado, contratos tipados e `ConversationEngine`.
- PR #30: adaptador OpenAI Responses, portas de memória/persistência e rota interna preparada.
- PR #31: anexos e execução controlada.
- PR #32: persistência PostgreSQL isolada.
- PR #33: ciclo controlado modelo → ferramenta → modelo.
- PR #34: ferramentas nativas da Responses API e continuidade por `call_id`.
- PR #35: configuração, composição, observabilidade e rota interna executável ainda não montada.
- PR #36: ferramentas reais locais e falhas recuperáveis.
- PR #37: políticas de risco, timeout, limites e rastreio multi-etapas.

Merge mais recente antes deste bloco: `feb29591ca282d684f42f0f807659a085eca75a5`.

## Bloco atual — conclusão da Fase 2

Branch: `feature/source-first-phase2-completion`

Inclui:
- ferramenta `normalize_text` para transformação determinística sem inventar conteúdo;
- ferramenta `extract_keywords` para leitura por frequência sem fontes externas;
- catálogo interno ampliado para quatro ferramentas seguras;
- `request_id` gerado quando ausente e preservado quando fornecido;
- correlação do `request_id` entre requisição, provedor, resultados e cada item do rastreio;
- fluxo determinístico com duas ferramentas de leitura/transformação no mesmo turno;
- testes de catálogo, normalização, palavras-chave, correlação e compatibilidade;
- CI atualizada;
- critério formal de saída da Fase 2 documentado.

## Próximo passo exato

1. Abrir o PR do bloco de conclusão da Fase 2.
2. Executar toda a CI.
3. Corrigir qualquer regressão comprovada sem retirar cobertura.
4. Integrar somente com CI verde.
5. Após o merge, iniciar a Fase 3 em bloco agrupado com:
   - escopo de memória por usuário e conversa;
   - modelo tipado para preferências, decisões, correções e restrições;
   - resumo controlado de contexto longo;
   - regras para evitar fatos inventados pela própria memória;
   - testes de continuidade conversacional.
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
