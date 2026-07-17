from pathlib import Path

# O DomnAI deve interpretar conversa livre pelo modelo principal, não por respostas fixas.
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

model_first_function = '''def _simple_conversation_response(message: str, attachments: list[dict], operation: str | None = None) -> str | None:
    # Não antecipa respostas por palavras-chave. O modelo principal recebe a mensagem,
    # o histórico, a memória e a operação ativa para interpretar a intenção real.
    return None
'''

contextual_signature = 'def _simple_conversation_response(message: str, attachments: list[dict], history: list[dict]) -> str | None:'
legacy_model_first_signature = 'def _simple_conversation_response(message: str, attachments: list[dict], operation: str | None = None) -> str | None:'

if contextual_signature in source:
    # O código-fonte já contém a implementação contextual mais nova.
    pass
elif legacy_model_first_signature in source:
    # Patch já aplicado em build anterior.
    pass
elif old_function in source:
    source = source.replace(old_function, model_first_function, 1)
else:
    raise RuntimeError('Função conversacional não encontrada em formato conhecido.')

old_call = '    simple_reply = _simple_conversation_response(message, safe_attachments)\n'
legacy_call = '    simple_reply = _simple_conversation_response(message, safe_attachments, operation)\n'
contextual_call = '    simple_reply = _simple_conversation_response(message, safe_attachments, history)\n'

if contextual_call in source or legacy_call in source:
    pass
elif old_call in source:
    source = source.replace(old_call, legacy_call, 1)
else:
    raise RuntimeError('Chamada da camada conversacional não encontrada em formato conhecido.')

path.write_text(source, encoding='utf-8')

# A operação permanece como conhecimento especializado, nunca como roteiro obrigatório.
prompt_path = Path('/app/app/services/domnai_brain.py')
prompt = prompt_path.read_text(encoding='utf-8')
marker = '20. Nunca afirme que criou, enviou ou compartilhou e-mail, planilha, arquivo ou link externo sem confirmação técnica.\n'
addition = (
    '20. Responda primeiro à intenção real da última mensagem do usuário, considerando o histórico completo. '
    'Converse de forma natural, contextual e humana, inclusive diante de cumprimentos, humor, ironia leve, comentários, '
    'reações, dúvidas sobre a própria conversa ou mudanças de assunto. Não use respostas pré-programadas nem transforme '
    'comentários sociais em consultas técnicas.\n'
    '21. Uma operação ativa fornece especialidade e objetivo, mas nunca substitui a interpretação da mensagem atual. '
    'Não siga a operação como formulário, não ignore desvios naturais e não repita perguntas. Quando a mensagem estiver '
    'relacionada à operação, prossiga tecnicamente; quando não estiver, responda normalmente e preserve o contexto para '
    'retomada posterior. Em mensagens mistas, responda aos dois conteúdos com transição natural.\n'
)
if 'Uma operação ativa fornece especialidade e objetivo' not in prompt:
    if marker not in prompt:
        raise RuntimeError('Ponto das regras centrais não encontrado para inserir comportamento model-first.')
    prompt = prompt.replace(marker, addition + marker, 1)

prompt_path.write_text(prompt, encoding='utf-8')
