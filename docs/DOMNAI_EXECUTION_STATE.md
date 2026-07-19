# DomnAI — Estado Atual da Execução

Atualizado em: 2026-07-19

## Repositório

- Repositório: `maxsantosmotta-web/domnai-backend`
- Branch principal: `main`
- Ambiente externo ativo: Railway
- Domínio: `https://domnai.iattomassist.com.br`

## Situação geral

- Fases 0 a 6: concluídas.
- Fase 7 de 8: em execução.
- Fluxo externo atual: backend legado.
- Novo núcleo: preparado para corte percentual controlado, ainda sem integração ao worker real neste bloco.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: ferramentas reais, políticas, rastreio e conclusão da Fase 2.
- PR #39 e #40: memória contextual e conclusão da Fase 3.
- PR #41 a #43: artefatos e conclusão da Fase 4.
- PR #44 e #45: API paralela, Clerk, feature flag e conclusão da Fase 5.
- PR #46 e #47: shadow mode, persistência comparativa, painel e conclusão da Fase 6.

Merge mais recente antes deste bloco: `2cf0b0b23ba4bbd0b7c5af22e64318e41b9c2710`.

## Bloco atual — fundação do corte controlado da Fase 7

Branch: `feature/source-first-phase7-controlled-cutover`

Inclui:
- configuração tipada `ControlledCutoverSettings`;
- feature flag `DOMNAI_CUTOVER_ENABLED`, desligada por padrão;
- percentual de tráfego determinístico por usuário e requisição;
- exigência opcional de aprovação prévia do shadow mode;
- bloqueio de anexos e follow-ups de artefato ainda não compatíveis;
- adaptação da resposta do novo núcleo para o contrato de cobrança atual;
- fallback automático ao legado em erro ou resposta vazia;
- proibição de desativar fallback antes de 100% do tráfego;
- propagação de usuário, conversa, memória e request_id;
- testes de configuração, elegibilidade, seleção, resposta real e fallback;
- CI ampliada.

## Regras de segurança deste bloco

- nenhuma resposta real muda enquanto a integração ao worker não for aplicada;
- corte permanece desligado por padrão;
- tráfego parcial exige fallback ativo;
- anexos e follow-ups de artefato continuam no legado;
- sem aprovação shadow, o novo núcleo não pode ser selecionado quando a exigência estiver ativa;
- erro ou resposta vazia do candidato volta ao legado;
- desligar `DOMNAI_CUTOVER_ENABLED` restaura seleção exclusiva do legado.

## Próximo passo exato

1. Abrir PR e executar CI completa.
2. Integrar somente com CI verde.
3. Acoplar o router ao ponto único de geração do worker legado.
4. Persistir métricas de rota, fallback, latência e erro.
5. Criar visão administrativa protegida de corte.
6. Iniciar em 0% e só elevar por decisão explícita após validação real.
7. Não remover o legado antes da Fase 8.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, confirmar PR e CI atuais e retomar exatamente do próximo passo registrado.
