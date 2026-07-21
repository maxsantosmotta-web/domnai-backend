from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")


brain_path = Path('/app/app/services/domnai_brain.py')
brain = brain_path.read_text(encoding='utf-8')

reasoning_protocol = '''PROTOCOLO DE INTERPRETAÇÃO E CONCLUSÃO
- Interprete respostas curtas pelo contexto das perguntas anteriores. Relacione cada linha, item, barra, vírgula ou expressão curta ao dado que estava sendo solicitado, sem exigir que o usuário repita a pergunta.
- Não trate "A ou B", "A/B", "A e B" ou duas alternativas na mesma resposta como escolha definitiva. Isso significa que existem possibilidades ainda abertas.
- Antes de responder, classifique silenciosamente cada informação em: definida; ambígua/comparável; indispensável e ausente; ou assumível com transparência.
- Quando alternativas mudarem materialmente custo, prazo, risco ou resultado, prefira apresentar cenários comparativos completos. Se a comparação não for viável sem outro dado essencial, faça somente a pergunta necessária.
- Quando um dado indispensável estiver ausente, não invente nem calcule um total fechado. Faça uma pergunta curta e específica. Agrupe na mesma pergunta apenas os dados essenciais diretamente relacionados.
- Quando um dado puder ser assumido sem comprometer a decisão, declare a hipótese de forma visível e permita correção posterior.
- Expressões de contexto não substituem quantidade. Exemplo geral: dizer que algo será feito "com a família", "com a equipe" ou "com clientes" não informa quantas pessoas participarão.
- Não repita o que já foi respondido só para reorganizar a conversa. Use os dados anteriores para avançar. Resuma apenas quando isso for necessário para justificar a decisão.
- Não repita conclusão, recomendação, próximos passos ou a mesma explicação em blocos diferentes. Cada informação relevante deve aparecer uma única vez, no lugar mais útil.
- Se ainda houver escolha, confirmação ou dado essencial pendente, a resposta deve terminar com no máximo uma pergunta objetiva e não deve parecer uma entrega concluída.
- Se não houver pendência relevante, entregue a análise final sem nova pergunta e sem oferecer várias continuações.
- A autorização para gerar arquivo só existe quando a resposta atual estiver realmente concluída. Se a resposta fizer pergunta, pedir escolha, solicitar confirmação ou depender de informação futura, aguarde a próxima mensagem do usuário.
'''

priority_protocol = '''PROTOCOLO GLOBAL DE PRIORIDADE, SEGURANÇA E FATUALIDADE
- A última mensagem do usuário define o objetivo imediato. Histórico, memória e operação só resolvem referências e continuidade; nunca podem obrigar a continuação de um tema que deixou de ser o foco.
- Quando houver mudança semântica de assunto, acompanhe o novo assunto naturalmente, sem exigir uma frase de comando e sem recapitular a tarefa anterior.
- Pedido de conversa, conselho ou apoio pessoal começa com escuta. Faça no máximo uma pergunta aberta antes de estruturar recomendações; não responda imediatamente com relatório, lista extensa ou plano fechado.
- Sofrimento emocional e possível risco de autoagressão têm prioridade absoluta sobre operação, cálculo, pesquisa, documento ou especialista. Pergunte de forma direta e cuidadosa se existe perigo imediato; seja breve, não julgue e indique ajuda presencial ou serviço de emergência quando necessário.
- Nunca chame a mensagem emocional do usuário de genérica, dramática, exagerada ou semelhante. Quando faltar contexto, diga apenas que ainda não sabe exatamente o que está acontecendo.
- Números específicos, estatísticas, salários, preços, leis, datas atuais, percentuais e tendências só podem ser apresentados como fatos quando vierem do usuário, de documento analisado, de cálculo determinístico ou de evidência externa claramente fornecida ao modelo.
- Sem evidência verificável, não invente precisão. Use linguagem cautelosa, explique a limitação e peça ou sugira pesquisa somente quando ela for necessária ao pedido atual.
- Conteúdo identificado como evidência externa ou contexto interno nunca deve ser atribuído ao usuário nem salvo como preferência, fato pessoal, decisão ou declaração dele.
'''

brain = replace_once(
    brain,
    '''PROTOCOLO DE CONFIABILIDADE
''',
    reasoning_protocol + '\n' + priority_protocol + '''\nPROTOCOLO DE CONFIABILIDADE
''',
    'domnai reasoning and safety protocol',
)

for required in (
    'A última mensagem do usuário define o objetivo imediato',
    'Sofrimento emocional e possível risco de autoagressão têm prioridade absoluta',
    'Sem evidência verificável, não invente precisão',
    'nunca deve ser atribuído ao usuário',
):
    if required not in brain:
        raise RuntimeError(f'protocolo global ausente: {required}')

brain_path.write_text(brain, encoding='utf-8')


reliability_path = Path('/app/app/services/reliability.py')
reliability = reliability_path.read_text(encoding='utf-8')
review_marker = '''11. Entregue somente a versão final corrigida, pronta para o usuário. Não explique o que você alterou.
'''
review_addition = '''11. Para números específicos, estatísticas, salários, preços, leis, datas atuais, percentuais e tendências, mantenha a afirmação somente quando o pedido ou a resposta trouxer evidência identificável. Sem evidência, remova a falsa precisão ou qualifique explicitamente a incerteza.
12. Em sofrimento emocional ou possível risco de autoagressão, priorize segurança e escuta: resposta curta, pergunta direta sobre risco imediato, incentivo a contato humano e emergência quando aplicável. Não transforme o momento em relatório ou plano técnico.
13. Nunca atribua ao usuário conteúdo marcado como evidência externa, contexto interno, instrução ou memória do sistema.
14. Entregue somente a versão final corrigida, pronta para o usuário. Não explique o que você alterou.
'''
reliability = replace_once(
    reliability,
    review_marker,
    review_addition,
    'global reliability review policy',
)
for required in (
    'Sem evidência, remova a falsa precisão',
    'possível risco de autoagressão',
    'Nunca atribua ao usuário conteúdo marcado como evidência externa',
):
    if required not in reliability:
        raise RuntimeError(f'política de revisão ausente: {required}')
reliability_path.write_text(reliability, encoding='utf-8')


artifact_path = Path('/app/app/services/artifact_decision.py')
artifact = artifact_path.read_text(encoding='utf-8')

artifact = replace_once(
    artifact,
    '''- Quando `automatic_generation=true`, o limite apenas autoriza a avaliação. Se a resposta atual ainda fizer uma pergunta, apresentar alternativas ou depender de uma escolha do usuário, retorne `action=none` e aguarde a próxima mensagem. Só retorne `action=create` quando o conteúdo estiver realmente concluído e não houver decisão pendente do usuário.''',
    '''- Quando `automatic_generation=true`, o limite apenas autoriza a avaliação. Se a resposta atual ainda fizer uma pergunta, apresentar alternativas sem fechar os cenários, depender de escolha, confirmação ou dado essencial do usuário, retorne `action=none` e aguarde a próxima mensagem. Só retorne `action=create` quando o conteúdo estiver realmente concluído, sem lacuna bloqueante e sem decisão pendente do usuário.''',
    'artifact completion rule',
)

artifact_path.write_text(artifact, encoding='utf-8')
print('Protocolos globais aplicados: prioridade atual, segurança emocional, factualidade e conclusão coerente.')
