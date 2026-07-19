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
- Fase 4 de 8: em execução.
- Fluxo externo atual: backend legado.
- Novo núcleo: isolado, sem montagem na rota principal.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: ferramentas reais, políticas, rastreio e conclusão da Fase 2.
- PR #39 e #40: memória contextual, conflito, expiração e conclusão da Fase 3.

Merge mais recente antes deste bloco: `d8bbab83947c8ab3b6e4b1e2aa9252e6b54fd64f`.

## Bloco atual — fundação da Fase 4

Branch: `feature/source-first-phase4-artifacts`

Inclui:
- contrato `Artifact` independente do legado;
- origem explícita `uploaded` ou `generated`;
- `ArtifactStore` substituível e implementação em memória;
- `ArtifactService` com registro, geração, leitura, listagem e recuperação;
- isolamento opcional por `owner_id`;
- geração de TXT, Markdown, JSON e CSV;
- leitura textual apenas de MIME types permitidos;
- limite individual de tamanho e limite textual;
- hash SHA-256 e resumo sem conteúdo bruto;
- separação de arquivos enviados e gerados;
- testes de formato, segurança, acesso, tamanho e determinismo;
- CI e roadmap atualizados.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir regressões sem retirar cobertura.
4. Integrar somente com CI verde.
5. Continuar a Fase 4 com:
   - persistência PostgreSQL isolada para artefatos;
   - geração real de PDF e XLSX somente sob pedido explícito;
   - política de autorização para geração;
   - integração controlada ao motor conversacional;
   - recuperação, expiração e preparação da Biblioteca.
6. Não montar a rota interna no `main.py` ainda.
7. Não alterar frontend nem tráfego de produção.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não acoplar artefatos ao backend legado;
- não gerar arquivos automaticamente sem pedido ou aceite contextual;
- não remover o backend legado;
- não alterar cobrança, Clerk, Stripe ou regras de créditos.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, o roadmap, confirmar PRs e CI atuais e retomar exatamente do próximo passo registrado.
