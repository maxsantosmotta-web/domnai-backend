from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

marker = '''          history,
          attachments: sentAttachments'''
replacement = '''          history,
          local_hour: new Date().getHours(),
          attachments: sentAttachments'''

if 'local_hour: new Date().getHours()' not in source:
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o payload persistente do chat para adicionar o horário local.')
    source = source.replace(marker, replacement, 1)

path.write_text(source, encoding='utf-8')
