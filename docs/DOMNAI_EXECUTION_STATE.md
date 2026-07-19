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
- Fase 2 de 8: concluída.
- Fase 3 de 8: em execução.
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
- PR #36: ferramentas reais locais e falhas recuperáveis.
- PR #37: políticas de risco, timeout, limites e rastreio multi-etapas.
- PR #38: catálogo seguro ampliado, correlação por solicitação e conclusão formal da Fase 2.

Merge mais recente antes deste bloco: `5c48a6cbc9293d6ad09a51486b1718fc1b97e6cd`.

## Bloco atual — início da Fase 3

Branch: `feature/source-first-phase3-memory-context`

Inclui:
- `ContextMemoryManager` isolado do backend legado;
- memória persistente separada por usuário e conversa;
- composição de preferências duráveis com decisões específicas da conversa;
- categorias explícitas: preferências, decisões, correções, restrições e fatos;
- fatos aceitos somente quando a origem é o próprio usuário;
- deduplicação e limites para impedir crescimento sem controle;
- resumo determinístico e limitado de históricos longos;
- carregamento automático do contexto estruturado no `ConversationEngine`;
- persistência de atualizações estruturadas após a resposta;
- compatibilidade com o comportamento anterior quando `user_id` não é informado;
- testes de separação, atualização, proteção, resumo e regressão;
- CI e roadmap atualizados.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir qualquer regressão comprovada sem retirar cobertura.
4. Integrar somente com CI verde.
5. Continuar a Fase 3 com:
   - persistência automática do resumo de contexto entre turnos;
   - expiração e substituição controlada de memória;
   - prioridade de correções recentes sobre decisões antigas;
   - instruções claras ao provedor para uso natural da memória;
   - testes de continuidade em múltiplos turnos.
6. Não montar a rota interna no `main.py` ainda.
7. Não alterar frontend nem tráfego de produção.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não ligar a nova memória ao chat externo;
- não remover o backend legado;
- não alterar cobrança, Clerk, Stripe ou regras de créditos;
- não persistir inferências do modelo como fatos do usuário.

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
