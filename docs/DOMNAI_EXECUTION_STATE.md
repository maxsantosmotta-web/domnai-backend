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
- PR #41: fundação segura de artefatos, formatos textuais e separação entre enviados e gerados.

Merge mais recente antes deste bloco: `fe888ed17b8c7742a16690be422dca3a1768cd89`.

## Bloco atual — persistência e binários da Fase 4

Branch: `feature/source-first-phase4-persistence-binary`

Inclui:
- persistência PostgreSQL isolada em `domnai_core_artifacts`;
- armazenamento íntegro de conteúdo binário e metadados;
- filtros por proprietário e origem;
- geração real de PDF com ReportLab;
- geração real de XLSX com openpyxl;
- autorização obrigatória por pedido explícito ou aceite contextual confirmado;
- bloqueio de registro binário sem prova de autorização;
- metadados de modo e origem da autorização;
- expiração opcional com ocultação em leitura e listagem;
- preservação de hash SHA-256 após persistência;
- testes de autorização, PDF, XLSX, expiração, isolamento e PostgreSQL;
- CI ampliada sem alterar produção.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir qualquer regressão comprovada sem retirar cobertura.
4. Integrar somente com CI verde.
5. Continuar a Fase 4 com:
   - integração controlada de artefatos ao motor conversacional;
   - recuperação e política de retenção da futura Biblioteca;
   - contratos de entrega sem exposição indevida do conteúdo bruto;
   - critério formal de saída da Fase 4.
6. Não montar a rota interna no `main.py` ainda.
7. Não alterar frontend nem tráfego de produção.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não acoplar artefatos ao backend legado;
- não gerar arquivos automaticamente sem pedido ou aceite contextual;
- não publicar arquivos externamente;
- não remover o backend legado;
- não alterar cobrança, Clerk, Stripe ou regras de créditos.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, o roadmap, confirmar PRs e CI atuais e retomar exatamente do próximo passo registrado.
