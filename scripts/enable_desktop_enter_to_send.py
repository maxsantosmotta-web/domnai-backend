from pathlib import Path
import re


DASHBOARD = Path('/frontend/src/Dashboard.jsx')
source = DASHBOARD.read_text(encoding='utf-8')

handler = "onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && window.innerWidth >= 768) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }}"

pattern = re.compile(
    r'<textarea\s+value=\{draft\}\s+onChange=\{\(event\)\s*=>\s*setDraft\(event\.target\.value\)\}(?:\s+onKeyDown=\{.*?\})?\s+(placeholder=\{.*?\}\s+rows="3"\s+disabled=\{.*?\}\s*/>)',
    re.S,
)

replacement = rf'<textarea value={{draft}} onChange={{(event) => setDraft(event.target.value)}} {handler} \1'
source, count = pattern.subn(replacement, source, count=1)

if count != 1:
    raise RuntimeError(f'Esperado localizar exatamente 1 campo principal de mensagem; localizado {count}.')

if handler not in source:
    raise RuntimeError('O manipulador de Enter não foi inserido no campo final do chat.')

DASHBOARD.write_text(source, encoding='utf-8')
print('Campo final confirmado: Enter envia no desktop e Shift+Enter quebra linha.')
