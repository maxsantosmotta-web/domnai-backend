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
- Fase 5 de 8: em execução.
- Fluxo externo atual: backend legado.
- Novo núcleo: isolado, sem substituir a rota principal.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: ferramentas reais, políticas, rastreio e conclusão da Fase 2.
- PR #39 e #40: memória contextual, conflito, expiração e conclusão da Fase 3.
- PR #41 a #43: artefatos, PostgreSQL, PDF/XLSX, autorização, Biblioteca e conclusão da Fase 4.

Merge mais recente antes deste bloco: `5140a5dba2a9acc8283f4ac284176d3a07b3f0ec`.

## Bloco atual — início acelerado da Fase 5

Branch: `feature/source-first-phase5-api-security`

Inclui:
- fábrica de rota paralela protegida, ainda sem substituir o fluxo externo;
- autenticação Bearer interna substituível;
- comparação de credencial em tempo constante;
- principal autenticado com escopos explícitos;
- autorização separada para status e resposta;
- correlação por `request_id` recebido ou gerado;
- propagação segura de usuário e conversa ao núcleo;
- eventos estruturados por rota, duração, status, usuário e erro;
- resposta sem exposição de segredo;
- testes de token ausente, token inválido, escopo, correlação e observabilidade;
- CI ampliada.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir regressões comprovadas sem retirar cobertura.
4. Integrar somente com CI verde.
5. Continuar a Fase 5 com:
   - configuração tipada das credenciais e feature flags;
   - composição oficial da API paralela;
   - montagem condicional e desligamento imediato;
   - autenticação compatível com o provedor real de identidade;
   - métricas e logs de aplicação;
   - critério formal de saída da Fase 5.
6. Não substituir a rota principal.
7. Não alterar o frontend nem direcionar tráfego real antes da Fase 6.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não montar rota paralela sem feature flag e autenticação;
- não expor credenciais em status ou logs;
- não remover o backend legado;
- não alterar cobrança, Clerk, Stripe ou regras de créditos.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, o roadmap, confirmar PRs e CI atuais e retomar exatamente do próximo passo registrado.
