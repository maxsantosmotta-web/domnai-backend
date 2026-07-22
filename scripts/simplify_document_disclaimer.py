from pathlib import Path

FINAL_NOTICE = (
    'Este documento organiza informações para apoio à decisão e não substitui '
    'a avaliação de um profissional habilitado.'
)

REPLACEMENTS = (
    (
        'Este documento organiza informações para apoio à decisão e não substitui a avaliação '
        'de profissional habilitado quando o tema exigir análise jurídica, contábil, médica, '
        'financeira ou técnica especializada.',
        FINAL_NOTICE,
    ),
    (
        'Este relatório organiza as informações fornecidas e não substitui avaliação profissional '
        'quando o tema exigir análise jurídica, contábil, médica, financeira ou técnica especializada.',
        FINAL_NOTICE,
    ),
    (
        'Este documento não substitui a avaliação de um profissional habilitado quando o tema exigir.',
        FINAL_NOTICE,
    ),
)

paths = (
    Path('/app/app/services/pdf_report.py'),
    Path('/app/app/services/spreadsheet_artifact.py'),
    Path('/app/app/api/chat.py'),
    Path('/app/app/services/chat_task_worker.py'),
)

for path in paths:
    source = path.read_text(encoding='utf-8')
    for old, new in REPLACEMENTS:
        source = source.replace(old, new)
    path.write_text(source, encoding='utf-8')

for path in paths:
    source = path.read_text(encoding='utf-8')
    if 'jurídica, contábil, médica' in source or 'quando o tema exigir' in source:
        raise RuntimeError(f'Aviso antigo permaneceu em {path}.')

print('Aviso simplificado aplicado exatamente em PDF, planilha, CSV e mensagem do chat.')
