# Classificação inicial dos scripts de build

Esta lista será atualizada durante a migração. A presença de um script no Docker não significa que seu comportamento será preservado.

## Migrar para código-fonte

- comportamento de encerramento contextual;
- decisões determinísticas de geração e entrega de artefatos;
- retenção e uso de histórico;
- roteamento de ferramentas e especialistas;
- persistência e estados funcionais do chat.

## Revisar antes de migrar

- regras textuais adicionadas ao prompt;
- ofertas automáticas de PDF;
- alterações de linguagem e formato da resposta;
- regras específicas criadas para corrigir testes isolados;
- patches que alteram o mesmo arquivo em sequência.

## Eliminar quando comprovadamente redundante

- patch já incorporado ao código-fonte;
- patch que não encontra mais o trecho original;
- regra que transforma a conversa em formulário;
- regra duplicada ou contraditória;
- alteração visual ou funcional coberta por implementação real posterior.

## Regra de execução

Cada remoção exige confirmação de equivalência no código-fonte, teste de regressão e revisão do diff antes da integração.
