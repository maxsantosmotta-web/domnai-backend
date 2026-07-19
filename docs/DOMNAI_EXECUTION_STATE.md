# DomnAI — Estado Atual da Execução

Atualizado em: 2026-07-19

## Repositório

- Repositório: `maxsantosmotta-web/domnai-backend`
- Branch principal: `main`
- Ambiente externo ativo: Railway
- Domínio: `https://domnai.iattomassist.com.br`

## Situação geral

- Fases 0 a 5: concluídas.
- Fase 6 de 8: concluída neste bloco, condicionada à CI verde e merge.
- Próxima fase: Fase 7 — corte controlado de produção.
- Fluxo externo atual: backend legado.
- Novo núcleo: validável em paralelo, sem substituir a resposta real.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: ferramentas reais, políticas, rastreio e conclusão da Fase 2.
- PR #39 e #40: memória contextual e conclusão da Fase 3.
- PR #41 a #43: artefatos e conclusão da Fase 4.
- PR #44 e #45: API paralela, Clerk, feature flag e conclusão da Fase 5.
- PR #46: shadow mode seguro e comparação sem efeitos colaterais.

## Bloco atual — conclusão da Fase 6

Branch: `feature/source-first-phase6-completion`

Inclui:
- worker shadow desacoplado do worker legado;
- execução somente quando a feature flag estiver ativa;
- leitura de tarefas concluídas sem alterar a resposta entregue;
- persistência PostgreSQL exclusiva de métricas seguras;
- nenhum prompt ou resposta bruta armazenado;
- painel administrativo protegido em `/api/admin/shadow-validation`;
- critérios objetivos de aprovação: amostra mínima, sucesso, resposta não vazia e similaridade média;
- rollback imediato ao desligar `DOMNAI_SHADOW_VALIDATION_ENABLED`;
- CI cobrindo regressão e conclusão da fase.

## Critério formal de saída da Fase 6

- legado permanece como única resposta real;
- candidato roda sem cobrança, artefatos, ferramentas ou memória persistente;
- comparativos são persistidos sem conteúdo bruto;
- falhas do candidato não afetam o usuário;
- administrador consegue consultar métricas e decisão objetiva de aprovação;
- o corte só pode ocorrer quando `approved=true` e após decisão explícita da Fase 7;
- desligar a flag interrompe novas validações no próximo ciclo/reinício.

## Próximo passo exato

1. Abrir PR e executar CI completa.
2. Integrar somente com CI verde.
3. Iniciar Fase 7 com roteamento percentual controlado, fallback automático e rollback.
4. Não remover o legado até validação real pós-corte.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, confirmar PR e CI atuais e retomar exatamente do próximo passo registrado.
