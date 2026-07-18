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

brain = replace_once(
    brain,
    '''PROTOCOLO DE CONFIABILIDADE
''',
    reasoning_protocol + '''\nPROTOCOLO DE CONFIABILIDADE
''',
    'domnai reasoning protocol',
)

brain_path.write_text(brain, encoding='utf-8')


artifact_path = Path('/app/app/services/artifact_decision.py')
artifact = artifact_path.read_text(encoding='utf-8')

artifact = replace_once(
    artifact,
    '''- Quando `automatic_generation=true`, o limite apenas autoriza a avaliação. Se a resposta atual ainda fizer uma pergunta, apresentar alternativas ou depender de uma escolha do usuário, retorne `action=none` e aguarde a próxima mensagem. Só retorne `action=create` quando o conteúdo estiver realmente concluído e não houver decisão pendente do usuário.''',
    '''- Quando `automatic_generation=true`, o limite apenas autoriza a avaliação. Se a resposta atual ainda fizer uma pergunta, apresentar alternativas sem fechar os cenários, depender de escolha, confirmação ou dado essencial do usuário, retorne `action=none` e aguarde a próxima mensagem. Só retorne `action=create` quando o conteúdo estiver realmente concluído, sem lacuna bloqueante e sem decisão pendente do usuário.''',
    'artifact completion rule',
)

artifact_path.write_text(artifact, encoding='utf-8')
