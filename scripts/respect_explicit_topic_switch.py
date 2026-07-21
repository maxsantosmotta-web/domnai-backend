from pathlib import Path


path = Path('/app/app/services/orchestrated_brain.py')
text = path.read_text(encoding='utf-8')

helper = '''\n\ndef _is_explicit_topic_switch(message: str) -> bool:\n    normalized = " ".join(\n        "".join(\n            char if char.isalnum() or char.isspace() else " "\n            for char in _normalized_text(message)\n        ).split()\n    )\n    if not normalized:\n        return False\n\n    switch_markers = (\n        "vamos mudar de assunto",\n        "vou mudar de assunto",\n        "mudando de assunto",\n        "quero mudar de assunto",\n        "quero falar de outra coisa",\n        "vamos falar de outra coisa",\n        "agora outro assunto",\n        "encerra esse assunto",\n        "pode encerrar esse assunto",\n        "deixa esse assunto",\n        "nao quero mais falar disso",\n        "vou mudar de ramo de atividades",\n    )\n    return any(marker in normalized for marker in switch_markers)\n'''

anchor = '\n\ndef _specialized_engine('
if '_is_explicit_topic_switch' not in text:
    if anchor not in text:
        raise RuntimeError('specialized engine anchor not found')
    text = text.replace(anchor, helper + anchor, 1)

old = '''    if _specialized_engine({}, operation, message) is None:\n        base_result = generate_metered_response(\n            message=message,\n            history=history,\n            operation=operation,\n            attachments=safe_attachments,\n            diagnosis_state=diagnosis_state,\n        )\n'''
new = '''    if _is_explicit_topic_switch(message):\n        base_result = generate_metered_response(\n            message=message,\n            history=[],\n            operation=None,\n            attachments=safe_attachments,\n            diagnosis_state=None,\n        )\n        return MeteredBrainResult(\n            text=base_result.text,\n            provider=f"topic-switch:{base_result.provider}",\n            model=base_result.model,\n            input_tokens=base_result.input_tokens,\n            output_tokens=base_result.output_tokens,\n            cached_input_tokens=base_result.cached_input_tokens,\n            diagnosis_state=base_result.diagnosis_state,\n            timings={"orchestrator_ms": 0, **(base_result.timings or {})},\n        )\n\n    if _specialized_engine({}, operation, message) is None:\n        base_result = generate_metered_response(\n            message=message,\n            history=history,\n            operation=operation,\n            attachments=safe_attachments,\n            diagnosis_state=diagnosis_state,\n        )\n'''
if new not in text:
    if old not in text:
        raise RuntimeError('direct routing block not found')
    text = text.replace(old, new, 1)

if 'provider=f"topic-switch:{base_result.provider}"' not in text:
    raise RuntimeError('topic switch route was not installed')

path.write_text(text, encoding='utf-8')
print('Explicit topic changes now clear the selected operation and specialist context.')
