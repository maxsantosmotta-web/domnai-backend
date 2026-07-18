from pathlib import Path


DASHBOARD = Path('/frontend/src/Dashboard.jsx')
source = DASHBOARD.read_text(encoding='utf-8')

old_pointer = """<textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && window.matchMedia('(pointer: fine)').matches) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder={uploading ? 'Salvando na biblioteca...' : 'Digite sua mensagem...'} rows="3" disabled={uploading} />"""
old_plain = """<textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={uploading ? 'Salvando na biblioteca...' : 'Digite sua mensagem...'} rows="3" disabled={uploading} />"""
new = """<textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && window.innerWidth >= 768) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder={uploading ? 'Salvando na biblioteca...' : 'Digite sua mensagem...'} rows="3" disabled={uploading} />"""

if new not in source:
    if old_pointer in source:
        source = source.replace(old_pointer, new, 1)
    elif old_plain in source:
        source = source.replace(old_plain, new, 1)
    else:
        raise RuntimeError('Campo principal de mensagem não localizado para configurar Enter.')

DASHBOARD.write_text(source, encoding='utf-8')
print('Enter envia em telas desktop; Shift+Enter mantém quebra de linha; celular preservado.')
