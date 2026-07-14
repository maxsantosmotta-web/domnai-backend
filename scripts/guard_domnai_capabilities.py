from pathlib import Path

path = Path('/app/app/services/metered_brain.py')
source = path.read_text(encoding='utf-8')

import_marker = 'from app.services.calculation_audit import ('
if 'from app.services.capability_guard import apply_capability_guard' not in source:
    if import_marker not in source:
        raise RuntimeError('Importações do cérebro não encontradas.')
    source = source.replace(import_marker, 'from app.services.capability_guard import apply_capability_guard\n' + import_marker, 1)

source = source.replace('text=text,\n        provider="replit-openai-gateway"', 'text=apply_capability_guard(text),\n        provider="replit-openai-gateway"', 1)
source = source.replace('text=preflight_text,\n            provider="openai-preflight-memory"', 'text=apply_capability_guard(preflight_text),\n            provider="openai-preflight-memory"', 1)
source = source.replace('"max_output_tokens": 500', '"max_output_tokens": 350')
source = source.replace('"max_output_tokens": 1200', '"max_output_tokens": 700')
source = source.replace('"max_output_tokens": 2400', '"max_output_tokens": 1400')

memory_marker = '''    updated_state, memory_usage = _update_diagnosis_memory(
        api_key,
        model,
        operation,
        diagnosis_state,
        message,
        final_text,
        attachments,
    )'''
if '    final_text = apply_capability_guard(final_text)\n\n' not in source:
    if memory_marker not in source:
        raise RuntimeError('Ponto de proteção da resposta final não encontrado.')
    source = source.replace(memory_marker, '    final_text = apply_capability_guard(final_text)\n\n' + memory_marker, 1)

path.write_text(source, encoding='utf-8')
