# DomnAI — Fase 8: aposentadoria segura do legado

A remoção do backend conversacional legado é proibida até o painel `/api/admin/legacy-retirement` retornar `ready=true`.

## Sequência obrigatória

1. Ativar `DOMNAI_CUTOVER_ENABLED=true` no Railway.
2. Elevar `DOMNAI_CUTOVER_TRAFFIC_PERCENT` gradualmente: 1, 5, 10, 25, 50 e 100.
3. Manter `DOMNAI_CUTOVER_FALLBACK_ENABLED=true` durante toda a validação.
4. Ao chegar a 100%, registrar `DOMNAI_FULL_CUTOVER_STARTED_AT` em ISO-8601 UTC.
5. Manter 100% por no mínimo 24 horas.
6. Acumular pelo menos 500 amostras.
7. Exigir taxa mínima de 99% de respostas do novo núcleo.
8. Exigir fallback máximo de 1%.
9. Confirmar a decisão com `DOMNAI_LEGACY_RETIREMENT_CONFIRMED=true`.
10. Somente depois abrir um PR separado para remover o legado.

## Rollback

Definir `DOMNAI_CUTOVER_ENABLED=false` e reiniciar o serviço. O fluxo volta integralmente ao legado enquanto ele ainda estiver presente.

## Regra de segurança

Este bloco não remove arquivos, funções, rotas ou dependências do legado. Ele apenas impede que a remoção aconteça sem evidência operacional suficiente.
