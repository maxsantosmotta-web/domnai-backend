# Contrato source-first do chat DomnAI

O DomnAI é um chat livre por padrão.

## Princípios obrigatórios

- A conversa vem antes das operações e módulos.
- Nenhuma operação é obrigatória para conversar.
- A operação selecionada fornece contexto e ferramentas, mas não impõe roteiro.
- O usuário pode mudar de assunto a qualquer momento.
- O histórico deve preservar decisões, correções e preferências sem repetir perguntas já respondidas.
- Respostas simples devem permanecer naturais e diretas.
- Relatórios, consolidações e arquivos só devem ser produzidos quando solicitados ou aceitos conscientemente pelo usuário.
- Comportamentos funcionais devem existir no código-fonte e ser protegidos por testes, não depender de remendos aplicados durante o Docker build.

## O que não deve voltar

- formulário disfarçado de conversa;
- sequência fixa de perguntas;
- obrigação de escolher uma operação;
- recapitulação completa a cada mensagem;
- oferta automática e repetitiva de PDF;
- scripts de build alterando silenciosamente o comportamento principal do chat.
