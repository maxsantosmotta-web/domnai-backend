from pathlib import Path


DASHBOARD = Path('/frontend/src/Dashboard.jsx')
source = DASHBOARD.read_text(encoding='utf-8')

old = '''<textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={uploading ? 'Salvando na biblioteca...' : 'Digite sua mensagem...'} rows="3" disabled={uploading} />'''
new = '''<textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && window.matchMedia('(pointer: fine)').matches) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder={uploading ? 'Salvando na biblioteca...' : 'Digite sua mensagem...'} rows="3" disabled={uploading} />'''

if new not in source:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'Esperado 1 campo principal de mensagem, encontrado {count}.')
    source = source.replace(old, new, 1)

DASHBOARD.write_text(source, encoding='utf-8')
print('Enter envia no desktop; Shift+Enter mantém quebra de linha; toque móvel preservado.')
