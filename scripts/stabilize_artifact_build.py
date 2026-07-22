from pathlib import Path
import re


def stabilize_frontend() -> None:
    path = Path('/frontend/src/Dashboard.jsx')
    if not path.exists():
        return

    source = path.read_text(encoding='utf-8')
    duplicate_attachments = re.compile(
        r'(?P<first>[ \t]*attachments:\s*sentAttachments\s*\n'
        r'[ \t]*\.filter\(\(item\) => item\.libraryId\)\s*\n'
        r'[ \t]*\.map\(\(item\) => \(\{ library_id: item\.libraryId \}\)\),\s*\n)'
        r'(?P=first)',
        flags=re.M,
    )
    source, count = duplicate_attachments.subn(r'\g<first>', source)

    if source.count('attachments: sentAttachments') > 1:
        raise RuntimeError('Mais de um campo de anexos permaneceu no payload final do chat.')

    path.write_text(source, encoding='utf-8')
    print(f'Frontend estabilizado: {count} bloco(s) duplicado(s) de anexos removido(s).')


def stabilize_runtime_patch() -> None:
    path = Path('/tmp/finalize_new_core_only.py')
    if not path.exists():
        return

    source = path.read_text(encoding='utf-8')
    unsafe = '''    artifact_result_anchor = '            "artifacts": artifacts,\\n'
    if 'artifacts = artifacts[:1]' not in source:
        position = source.find(artifact_result_anchor)
        if position < 0:
            raise RuntimeError('Resultado de artefatos não localizado no worker final.')
        source = source[:position] + '        artifacts = artifacts[:1]\\n' + source[position:]

'''
    if unsafe in source:
        source = source.replace(unsafe, '', 1)

    if "artifacts = artifacts[:1]" in source:
        raise RuntimeError('Inserção insegura de limite de artefatos permaneceu no patch final.')

    path.write_text(source, encoding='utf-8')
    compile(source, str(path), 'exec')
    print('Patch final estabilizado: limite de um arquivo preservado pela persistência canônica.')


stabilize_frontend()
stabilize_runtime_patch()
