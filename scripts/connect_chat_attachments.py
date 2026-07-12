from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

target = """          message: messageForApi,
          operation: operationName,
          history,
"""
replacement = """          message: messageForApi,
          operation: operationName,
          history,
          attachments: sentAttachments
            .filter((item) => item.libraryId)
            .map((item) => ({ library_id: item.libraryId })),
"""

if target not in source:
    raise RuntimeError('Não foi possível conectar os anexos ao envio do chat.')

source = source.replace(target, replacement, 1)
path.write_text(source, encoding='utf-8')
