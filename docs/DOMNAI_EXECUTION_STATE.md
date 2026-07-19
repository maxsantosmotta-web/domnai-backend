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
- Fase 4 de 8: concluída neste bloco, condicionada à CI verde e merge.
- Próxima fase: Fase 5 — API paralela, autenticação e observabilidade.
- Fluxo externo atual: backend legado.
- Novo núcleo: isolado, sem montagem na rota principal.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: ferramentas reais, políticas, rastreio e conclusão da Fase 2.
- PR #39 e #40: memória contextual, conflito, expiração e conclusão da Fase 3.
- PR #41: fundação segura de artefatos e formatos textuais.
- PR #42: PostgreSQL, PDF, XLSX, autorização e expiração.

Merge mais recente antes deste bloco: `0aced682b610c4dbb79fd4fcde7a486ff78b1efe`.

## Bloco atual — encerramento da Fase 4

Branch: `feature/source-first-phase4-completion`

Inclui:
- contrato estruturado `ArtifactIntent`;
- proibição de inferir geração automaticamente pela mensagem;
- `ArtifactCoordinator` para intenção, autorização, retenção e Biblioteca;
- `ArtifactAwareConversationEngine` opcional, preservando o motor base;
- geração após resposta conversacional concluída;
- autorização novamente validada no ponto de execução;
- associação segura por usuário e conversa;
- retenção opcional por prazo;
- visibilidade configurável na futura Biblioteca;
- listagem segura sem conteúdo bruto;
- testes de ausência de efeito sem intenção, bloqueio sem autorização, geração real, retenção e Biblioteca;
- critério formal de saída da Fase 4.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir qualquer regressão comprovada sem retirar cobertura.
4. Integrar somente com CI verde.
5. Após o merge, iniciar a Fase 5 com:
   - rota paralela protegida e desligada por padrão;
   - autenticação e autorização próprias;
   - composição do núcleo completo;
   - correlação, logs e métricas externos;
   - feature flag e desligamento imediato;
   - testes de API sem substituir o legado.
6. Não substituir a rota principal.
7. Não alterar o frontend nem direcionar tráfego real antes da Fase 6.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não acoplar artefatos ao backend legado;
- não publicar arquivos externamente;
- não montar rota pública sem autenticação;
- não remover o backend legado;
- não alterar cobrança, Clerk, Stripe ou regras de créditos.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, o roadmap, confirmar PRs e CI atuais e retomar exatamente do próximo passo registrado.
