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
- Fase 3 de 8: concluída.
- Fase 4 de 8: concluída.
- Fase 5 de 8: concluída neste bloco, condicionada à CI verde e merge.
- Próxima fase: Fase 6 — integração com frontend e validação comparativa.
- Fluxo externo atual: backend legado.
- Novo núcleo: montável em paralelo somente por feature flag, sem substituir a rota principal.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: ferramentas reais, políticas, rastreio e conclusão da Fase 2.
- PR #39 e #40: memória contextual, conflito, expiração e conclusão da Fase 3.
- PR #41 a #43: artefatos, PostgreSQL, PDF/XLSX, autorização, Biblioteca e conclusão da Fase 4.
- PR #44: API paralela protegida, escopos, correlação e observabilidade externa.

## Bloco atual — encerramento da Fase 5

Branch: `feature/source-first-phase5-completion`

Inclui:
- configuração tipada por ambiente;
- feature flag `DOMNAI_PARALLEL_API_ENABLED`, desligada por padrão;
- montagem condicional sem alterar rotas legadas;
- rollback imediato ao desligar a flag;
- modos de autenticação `clerk` e `static`;
- adaptador para o verificador Clerk já existente;
- autenticação estática restrita a uso interno e obrigatoriamente configurada;
- escopos explícitos e configuráveis;
- eventos e métricas preservados;
- testes de rota ausente quando desabilitada, montagem protegida, Clerk e configuração inválida;
- critério formal de saída da Fase 5.

## Critério de saída da Fase 5

- API paralela não existe externamente por padrão;
- habilitação exige feature flag explícita;
- autenticação e autorização são obrigatórias;
- identidade Clerk existente pode ser reutilizada sem duplicar regras;
- desligar a flag remove a superfície paralela no próximo reinício/deploy;
- legado continua sendo o único fluxo ativo até a Fase 6;
- CI cobre o fluxo novo e todas as fases anteriores.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir regressões comprovadas sem retirar cobertura.
4. Integrar somente com CI verde.
5. Iniciar a Fase 6 com validação comparativa controlada entre legado e novo núcleo.
6. Não direcionar tráfego real sem amostragem, métricas e rollback definidos.
7. Não remover o backend legado.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, o roadmap, confirmar PRs e CI atuais e retomar exatamente do próximo passo registrado.
