# Consolidação segura dos patches de runtime

Branch de auditoria criada a partir de `main` para consolidar correções hoje aplicadas durante o Docker build, sem alterar produção.

## Ordem real dos patches de backend

1. `scripts/connect_chat_sources_backend.py`
2. `scripts/instrument_chat_pipeline.py`
3. `scripts/tune_domnai_responses.py`
4. `scripts/guard_domnai_capabilities.py`
5. `scripts/apply_stages_9_11.py`

## Contrato funcional que não pode regredir

- Fontes reais persistidas no histórico e URLs inválidas filtradas.
- Tempos de fila, preparação, pesquisa, orquestrador, geração, auditoria, revisão, memória, artefato, cobrança e persistência registrados.
- Histórico normalizado limitado a 10 mensagens e 6.000 caracteres por mensagem.
- Respostas comuns limitadas e objetivas; respostas extensas apenas quando exigidas.
- Proteção contra afirmações falsas de arquivo, link, e-mail ou capacidade inexistente.
- Feedback bloqueado no backend para Free e liberado para Premium/administrador.
- Consulta de status financeiro não cria conta antecipadamente.

## Estratégia de consolidação

1. Incorporar no código-fonte exatamente o resultado de cada patch, preservando a ordem atual.
2. Manter temporariamente os scripts no Docker para comprovar idempotência.
3. Construir a imagem e confirmar que todos os scripts executam sem alterar novamente os arquivos já consolidados.
4. Comparar o comportamento final com a produção atual.
5. Remover um script por vez somente após equivalência comprovada.
6. Alterar `alembic upgrade heads` para `alembic upgrade head` apenas depois da migração de merge e confirmação de uma única head.

## Critério para marcar o item 14 como concluído

O código versionado precisa ser o mesmo código executado no Railway, sem reescrita de arquivos principais durante o build e sem regressão nos fluxos acima.
