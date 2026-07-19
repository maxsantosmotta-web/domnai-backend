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
- Fase 3 de 8: concluída neste bloco, condicionada à CI verde e merge.
- Próxima fase: Fase 4 — arquivos, relatórios e artefatos.
- Fluxo externo atual: backend legado.
- Novo núcleo: isolado, sem montagem na rota principal.

## Concluído e integrado na main

- PR #29 a #35: fundação, ferramentas, persistência, observabilidade e composição.
- PR #36 a #38: execução real de ferramentas, políticas, rastreio e conclusão da Fase 2.
- PR #39: memória contextual por usuário e conversa, categorias estruturadas e proteção factual.

Merge mais recente antes deste bloco: `e8f391c804c94b7f3797a8c4dfe2f861de32dfc2`.

## Bloco atual — encerramento da Fase 3

Branch: `feature/source-first-phase3-completion`

Inclui:
- resumo de históricos longos persistido entre turnos;
- substituição de memória por chave;
- correções recentes prevalecendo sobre preferências, decisões, restrições e fatos conflitantes;
- expiração opcional por item com poda automática;
- preservação da origem e bloqueio de fatos inferidos;
- orientação explícita para uso natural e discreto da memória;
- instrução ao provedor para reconhecer conflito e incerteza;
- testes de conflito, expiração, persistência de resumo, orientação natural e regressão;
- critério formal de saída da Fase 3.

## Próximo passo exato

1. Abrir o PR deste bloco.
2. Executar toda a CI.
3. Corrigir qualquer regressão comprovada sem retirar cobertura.
4. Integrar somente com CI verde.
5. Após o merge, iniciar a Fase 4 em bloco agrupado com:
   - leitura segura de anexos;
   - geração de PDF, XLSX e CSV somente sob pedido;
   - armazenamento e recuperação isolados;
   - separação entre arquivos enviados e gerados;
   - validação de formato, tamanho e conteúdo.
6. Não montar a rota interna no `main.py` ainda.
7. Não alterar frontend nem tráfego de produção.

## O que não deve ser feito agora

- não substituir a rota de produção;
- não alterar frontend;
- não ligar a nova memória ao chat externo;
- não remover o backend legado;
- não alterar cobrança, Clerk, Stripe ou regras de créditos;
- não persistir inferências do modelo como fatos do usuário.

## Regra de retomada por outra janela

A próxima janela deve ler este arquivo, o roadmap, confirmar PRs e CI atuais e retomar exatamente do próximo passo registrado.
