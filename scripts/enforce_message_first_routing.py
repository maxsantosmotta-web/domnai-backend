from pathlib import Path


path = Path('/app/app/services/orchestrated_brain.py')
source = path.read_text(encoding='utf-8')

# Regra estrutural: a operação selecionada é contexto para o planejador, nunca
# autorização suficiente para capturar a mensagem no motor especialista.
function_start = source.index('def _specialized_engine(')
function_end = source.index('\n\ndef generate_orchestrated_response(', function_start)
message_first_engine = '''def _specialized_engine(plan: dict, operation: str | None, message: str) -> str | None:
    del operation  # pista de interface; não decide o roteamento
    engine_text = _normalized_text(plan.get("specialized_engine"))
    message_text = _normalized_text(message)

    plan_markers = ("labor_termination", "rescisao", "trabalhista", "labor")
    if any(marker in engine_text for marker in plan_markers):
        return "labor_termination"

    # Fallback determinístico apenas para pedidos inequivocamente trabalhistas
    # quando o planejador falhar. Não inclui saudações, desabafos ou troca de tema.
    explicit_labor_requests = (
        "calcular minha rescisao",
        "calculo de rescisao",
        "recalcular minha rescisao",
        "revisar calculo trabalhista",
        "verbas rescisorias",
        "demissao sem justa causa",
        "pedido de demissao",
        "aviso previo proporcional",
        "ferias proporcionais na rescisao",
        "decimo terceiro proporcional na rescisao",
    )
    if any(marker in message_text for marker in explicit_labor_requests):
        return "labor_termination"

    return None
'''
source = source[:function_start] + message_first_engine.rstrip() + source[function_end:]

# Remove todos os atalhos anteriores que decidiam antes do planejador usando a
# operação selecionada ou frases de troca de assunto. Toda mensagem não leve
# passa primeiro pelo planejador semântico.
generate_start = source.index('def generate_orchestrated_response(')
api_key_anchor = source.index('    api_key = os.getenv("OPENAI_API_KEY", "").strip()', generate_start)
light_anchor = source.rfind('    if _is_light_conversation(message, safe_attachments):', generate_start, api_key_anchor)
if light_anchor < 0:
    raise RuntimeError('bloco de conversa leve não encontrado')
light_return_end = source.index('\n', source.index('        return _light_conversation_response(', light_anchor)) + 1
source = source[:light_return_end] + '\n' + source[api_key_anchor:]

# Após o planejamento, somente a intenção apurada pode ativar o especialista.
# Quando não houver intenção especializada, a geração geral recebe operation=None
# para impedir que o rótulo visual contamine a resposta livre.
old_general = '''    base_result = generate_metered_response(
        message=message,
        history=history,
        operation=operation,
        attachments=safe_attachments,
        diagnosis_state=diagnosis_state,
    )
'''
new_general = '''    base_result = generate_metered_response(
        message=message,
        history=history,
        operation=None,
        attachments=safe_attachments,
        diagnosis_state=diagnosis_state,
    )
'''
last_general = source.rfind(old_general)
if last_general < 0:
    if new_general not in source:
        raise RuntimeError('rota geral final não encontrada')
else:
    source = source[:last_general] + new_general + source[last_general + len(old_general):]

for forbidden in (
    'if operation_text == labor_operation:',
    'if _is_explicit_topic_switch(message):',
    'if _specialized_engine({}, operation, message) is None:',
):
    if forbidden in source:
        raise RuntimeError(f'regra antiga permaneceu no runtime: {forbidden}')

required = (
    'del operation  # pista de interface; não decide o roteamento',
    'engine = _specialized_engine(plan, operation, message)',
    'operation=None,',
)
for marker in required:
    if marker not in source:
        raise RuntimeError(f'regra message-first ausente: {marker}')

path.write_text(source, encoding='utf-8')
print('Roteamento absoluto instalado: mensagem atual decide; operação é apenas contexto do planejador.')
