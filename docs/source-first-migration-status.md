# Migração source-first — estado atual

## Concluído

- Despedidas simples continuam locais no começo da conversa.
- Depois de uma conversa produtiva, o encerramento volta para a inteligência contextual.
- Testes gerais do chat e backend foram estabilizados.
- Primeiro bloco foi integrado à `main` pelo PR #26.

## Em andamento

- Proteção automatizada do chat livre.
- Registro explícito de que operações são contexto, não roteiro obrigatório.
- Separação entre comportamentos reais do código-fonte e alterações silenciosas feitas durante o Docker build.

## Próximos blocos

1. Mapear quais scripts de build ainda alteram o núcleo conversacional.
2. Classificar cada alteração como manter, migrar ou eliminar.
3. Migrar somente comportamentos necessários para o código-fonte.
4. Remover do Docker cada remendo já absorvido.
5. Executar testes, revisar diff, integrar e validar em produção.
