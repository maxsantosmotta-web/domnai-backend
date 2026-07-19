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
- Fase 5 de 8: concluída.
- Fase 6 de 8: em execução.
- Fluxo externo atual: backend legado.
- Novo núcleo: disponível em superfície paralela protegida, desligada por padrão.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: ferramentas reais, políticas, rastreio e conclusão da Fase 2.
- PR #39 e #40: memória contextual, conflito, expiração e conclusão da Fase 3.
- PR #41 a #43: artefatos, PostgreSQL, PDF/XLSX, autorização, Biblioteca e conclusão da Fase 4.
- PR #44 e #45: API paralela, segurança, Clerk, feature flag e conclusão da Fase 5.

Merge mais recente antes deste bloco: `efd77f969768b3ded20f0916dd08a509e006c71a`.

## Bloco atual — validação comparativa da Fase 6

Branch: `feature/source-first-phase6-shadow-validation`

Inclui:
- `ShadowValidationSettings` com feature flag desligada por padrão;
- amostragem percentual determinística por usuário e requisição;
- execução candidata isolada, sem PostgreSQL, ferramentas, cobrança ou artefatos;
- comparação segura entre resposta legada e candidata;
- métricas de comprimento, similaridade, provedor e falha;
- proibição de registrar o texto bruto das respostas;
- falhas do candidato isoladas da resposta entregue ao usuário;
- agendamento assíncrono em thread daemon para não bloquear o fluxo legado;
- timeout próprio do candidato;
- testes de configuração, amostragem, privacidade, sucesso e falha;
- CI ampliada.

## Regras de segurança deste bloco

- shadow mode não executa por padrão;
- habilitação exige `DOMNAI_SHADOW_VALIDATION_ENABLED=true`;
- amostragem exige `DOMNAI_SHADOW_SAMPLE_PERCENT` entre 1 e 100;
- a resposta legada continua sendo a única devolvida ao usuário;
- o candidato não cobra créditos, não gera arquivos e não altera memória persistente;
- qualquer falha do candidato é registrada e descartada sem afetar o usuário;
- nenhum tráfego do frontend é redirecionado.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir regressões comprovadas sem retirar cobertura.
4. Integrar somente com CI verde.
5. Em seguida concluir a Fase 6 com integração controlada ao worker legado, painel/relatório comparativo e critérios formais de equivalência.
6. Não promover o novo núcleo para resposta real antes da Fase 7.
7. Não remover o backend legado.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, o roadmap, confirmar PRs e CI atuais e retomar exatamente do próximo passo registrado.
