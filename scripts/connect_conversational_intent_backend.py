from pathlib import Path

path = Path('/app/app/services/orchestrated_brain.py')
source = path.read_text(encoding='utf-8')

old_function = '''def _simple_conversation_response(message: str, attachments: list[dict]) -> str | None:
    if attachments:
        return None

    normalized = " ".join(_normalized_text(message).replace("?", "").replace("!", "").split())
    if not normalized or len(normalized) > 80:
        return None

    greeting_messages = {
        "oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai",
        "chat tudo bem", "chat, tudo bem", "tudo bem", "como voce esta", "como vai",
    }
    thanks_messages = {
        "obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu", "agradecido", "agradecida",
    }
    confirmation_messages = {
        "ok", "certo", "entendi", "beleza", "perfeito", "combinado", "pode continuar",
    }
    farewell_messages = {
        "tchau", "ate mais", "boa noite chat", "falamos depois", "ate logo",
    }

    if normalized in greeting_messages:
        return "Tudo ótimo! E com você? Como posso ajudar hoje?"
    if normalized in thanks_messages:
        return "Por nada! Estou à disposição para continuar."
    if normalized in confirmation_messages:
        return "Perfeito. Vamos continuar."
    if normalized in farewell_messages:
        return "Até mais! Quando precisar, é só chamar."
    return None
'''

new_function = '''def _simple_conversation_response(message: str, attachments: list[dict], operation: str | None = None) -> str | None:
    if attachments:
        return None

    normalized = " ".join(
        _normalized_text(message)
        .replace("?", " ")
        .replace("!", " ")
        .replace(",", " ")
        .replace(".", " ")
        .split()
    )
    if not normalized or len(normalized) > 180:
        return None

    thanks_messages = {
        "obrigado", "obrigada", "muito obrigado", "muito obrigada", "valeu", "agradecido", "agradecida",
    }
    confirmation_messages = {
        "ok", "certo", "entendi", "beleza", "perfeito", "combinado", "pode continuar",
    }
    farewell_messages = {
        "tchau", "ate mais", "boa noite chat", "falamos depois", "ate logo",
    }
    confusion_markers = (
        "nao entendi", "explica melhor", "pode explicar", "ficou confuso", "nao ficou claro",
    )
    reaction_markers = (
        "ai e brabo", "isso e brabo", "e complicado", "caramba", "nossa", "pesado isso",
    )
    assistant_mood_markers = (
        "voce esta estressado", "voce ta estressado", "esta estressado hoje", "ta estressado hoje",
        "voce esta bravo", "voce ta bravo", "esta bravo hoje", "ta bravo hoje",
        "voce esta serio", "voce ta serio", "esta serio hoje", "ta serio hoje",
        "esta de mau humor", "ta de mau humor", "poucas palavras", "respondeu seco",
        "respondeu diferente", "resposta seca", "parece distante", "parece frio",
        "por que respondeu assim", "porque respondeu assim", "me tratou com indiferenca",
    )
    assistant_wellbeing_markers = (
        "como voce esta", "como vai voce", "como vai", "como esta hoje", "tudo bem com voce",
        "como voce ta", "como ce ta",
    )
    social_clarification_markers = (
        "nao estou buscando nada", "so queria saber como esta", "apenas querendo saber como esta",
        "so estou conversando", "so queria conversar", "estou falando de voce",
    )

    # Comentários sobre o próprio DomnAI são conversa social, não consulta sobre saúde ou pesquisa.
    if any(marker in normalized for marker in assistant_mood_markers):
        return "Não estou bravo nem estressado 😄 Se pareci mais direto, foi só pelo jeito da resposta. Pode falar comigo normalmente."
    if any(marker in normalized for marker in social_clarification_markers):
        return "Entendi 😄 Estou bem e por aqui para conversar com você. Como você está hoje?"
    if any(marker in normalized for marker in assistant_wellbeing_markers):
        return "Estou bem e pronto para conversar. E você, como está?"

    if normalized.startswith("bom dia"):
        return "Bom dia! Como você está?"
    if normalized.startswith("boa tarde"):
        return "Boa tarde! Como você está?"
    if normalized.startswith("boa noite"):
        return "Boa noite! Como você está?"
    if normalized.startswith(("fala chat", "oi chat", "ola chat", "e ai chat")):
        return "Fala! Tudo certo por aqui. E com você?"
    if normalized in {"oi", "ola", "e ai"}:
        return "Oi! Tudo bem com você?"
    if normalized in thanks_messages:
        return "Por nada! Seguimos quando você quiser."
    if normalized in confirmation_messages:
        return "Perfeito. Vamos continuar no seu ritmo."
    if normalized in farewell_messages:
        return "Até mais! Quando precisar, é só chamar."
    if any(marker in normalized for marker in confusion_markers):
        return "Claro. Vou explicar de um jeito mais simples e por partes. Qual trecho ficou confuso para você?"
    if any(marker in normalized for marker in reaction_markers):
        return "É, pode parecer bastante coisa de uma vez. Vamos com calma e por partes."
    return None
'''

if old_function not in source:
    raise RuntimeError('Função de conversa simples não encontrada no formato esperado.')
source = source.replace(old_function, new_function, 1)

old_call = '    simple_reply = _simple_conversation_response(message, safe_attachments)\n'
new_call = '    simple_reply = _simple_conversation_response(message, safe_attachments, operation)\n'
if old_call not in source:
    raise RuntimeError('Chamada da camada conversacional não encontrada.')
source = source.replace(old_call, new_call, 1)

path.write_text(source, encoding='utf-8')

prompt_path = Path('/app/app/services/domnai_brain.py')
prompt = prompt_path.read_text(encoding='utf-8')
marker = '20. Nunca afirme que criou, enviou ou compartilhou e-mail, planilha, arquivo ou link externo sem confirmação técnica.\n'
addition = (
    '20. Antes de seguir qualquer operação ativa, interprete e responda à intenção da última mensagem do usuário. '
    'A operação é contexto especializado, não um roteiro obrigatório. Se o usuário cumprimentar, agradecer, reagir, '
    'brincar, comentar sobre o tom do próprio DomnAI, pedir explicação ou fizer uma pergunta natural, responda a isso '
    'primeiro. Não transforme comentários dirigidos ao assistente em consulta médica, pesquisa ou análise temática. '
    'Não ignore a mensagem, não repita a pergunta operacional anterior e não pareça um formulário. Mantenha a operação '
    'disponível para continuidade natural.\n'
    '21. Em mensagens mistas, responda primeiro ao conteúdo conversacional e depois retome a operação em uma frase curta, '
    'sem repetir perguntas já feitas ou respondidas.\n'
)
if 'A operação é contexto especializado, não um roteiro obrigatório.' not in prompt:
    if marker not in prompt:
        raise RuntimeError('Ponto das regras centrais não encontrado para inserir prioridade conversacional.')
    prompt = prompt.replace(marker, addition + marker, 1)

prompt_path.write_text(prompt, encoding='utf-8')