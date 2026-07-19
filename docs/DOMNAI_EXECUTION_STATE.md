# DomnAI — Estado Atual da Execução

Atualizado em: 2026-07-19

## Repositório

- Repositório: `maxsantosmotta-web/domnai-backend`
- Branch principal: `main`
- Ambiente externo ativo: Railway
- Domínio: `https://domnai.iattomassist.com.br`

## Situação geral

- Fases 0 a 6: concluídas.
- Fase 7 de 8: concluída tecnicamente neste bloco, condicionada à CI verde e merge.
- Fluxo externo atual: backend legado, porque `DOMNAI_CUTOVER_ENABLED` permanece desligada e o percentual permanece em 0%.
- Novo núcleo: integrado ao ponto único do worker, pronto para ativação percentual controlada.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: ferramentas reais, políticas, rastreio e conclusão da Fase 2.
- PR #39 e #40: memória contextual e conclusão da Fase 3.
- PR #41 a #43: artefatos e conclusão da Fase 4.
- PR #44 e #45: API paralela, Clerk, feature flag e conclusão da Fase 5.
- PR #46 e #47: shadow mode, persistência comparativa, painel e conclusão da Fase 6.
- PR #48: fundação do corte percentual, seleção determinística e fallback.

## Bloco atual — conclusão da Fase 7

Branch: `feature/source-first-phase7-completion`

Inclui:
- integração do roteador no ponto único de geração do worker;
- contexto seguro por thread com usuário, tarefa e follow-up de artefato;
- releitura da configuração por tarefa para rollback imediato;
- persistência PostgreSQL de rota, fallback, motivo e latência;
- nenhuma persistência de prompt ou resposta bruta;
- painel administrativo protegido em `/api/admin/cutover`;
- readiness para corte integral baseado em aprovação shadow, amostra e fallback;
- corte desligado por padrão e tráfego mantido em 0%;
- testes de rollback, integração e preservação de métricas;
- CI completa de todas as fases.

## Critério formal de saída da Fase 7

- o worker real possui um único ponto de decisão entre legado e novo núcleo;
- `DOMNAI_CUTOVER_ENABLED=false` mantém 100% no legado;
- configuração inválida volta ao legado;
- tráfego parcial sempre exige fallback;
- anexos e artefatos incompatíveis permanecem no legado;
- métricas administrativas não guardam conteúdo conversacional;
- falha ou resposta vazia do novo núcleo retorna ao legado;
- o legado permanece disponível para rollback até a Fase 8.

## Próximo passo exato

1. Abrir PR e executar CI completa.
2. Integrar somente com CI verde.
3. Manter corte em 0% até decisão explícita e configuração do Railway.
4. Executar validação real gradual: 1%, 5%, 10%, 25%, 50% e 100%, observando o painel.
5. Só após estabilidade real iniciar a Fase 8 para remoção do legado.

## Regra de retomada por outra janela

A próxima janela deve confirmar PR, CI, flags reais do Railway e percentual atual antes de qualquer promoção de tráfego.
