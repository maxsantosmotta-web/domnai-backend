from pathlib import Path
import re


ARTIFACT_DECISION_PATH = Path('/app/app/services/artifact_decision.py')
WORKER_PATH = Path('/app/app/services/chat_task_worker.py')
CHAT_API_PATH = Path('/app/app/api/chat.py')
DASHBOARD_PATH = Path('/frontend/src/Dashboard.jsx')


def write_python(path: Path, source: str) -> None:
    compile(source, str(path), 'exec')
    path.write_text(source, encoding='utf-8')


def patch_artifact_source_selection() -> None:
    source = ARTIFACT_DECISION_PATH.read_text(encoding='utf-8')
    anchor = '''        normalized = _normalize(content)
        if "openai respondeu http" in normalized or "nao foi possivel" in normalized:
            continue
'''
    replacement = '''        normalized = _normalize(content)
        invalid_artifact_source = (
            "openai respondeu http" in normalized
            or "nao foi possivel" in normalized
            or "sandbox mnt data" in normalized
            or "arquivo foi gerado" in normalized
            or "arquivo criado e enviado" in normalized
            or "pdf criado e enviado" in normalized
            or ("aqui esta o pdf" in normalized and "clique no link" in normalized)
        )
        if invalid_artifact_source:
            continue
'''
    if replacement not in source:
        if anchor not in source:
            raise RuntimeError('Seleção da última resposta útil não localizada em artifact_decision.py.')
        source = source.replace(anchor, replacement, 1)
    write_python(ARTIFACT_DECISION_PATH, source)


def remove_backend_post_artifact_messages() -> None:
    worker = WORKER_PATH.read_text(encoding='utf-8')
    worker, worker_count = re.subn(
        r'^\s*"post_artifact_text"\s*:\s*.*?if artifacts else "",\s*\n',
        '',
        worker,
        count=1,
        flags=re.MULTILINE,
    )
    if '"post_artifact_text"' in worker:
        raise RuntimeError('A segunda mensagem posterior ainda existe no worker.')
    write_python(WORKER_PATH, worker)

    chat_api = CHAT_API_PATH.read_text(encoding='utf-8')
    chat_api, api_count = re.subn(
        r'^\s*"postArtifactText"\s*:\s*POST_ARTIFACT_TEXT if artifact else "",\s*\n',
        '',
        chat_api,
        count=1,
        flags=re.MULTILINE,
    )
    if '"postArtifactText"' in chat_api:
        raise RuntimeError('A segunda mensagem posterior ainda existe na API do chat.')
    write_python(CHAT_API_PATH, chat_api)

    if worker_count == 0 and api_count == 0:
        print('Avisos posteriores já estavam ausentes no backend.')


def remove_frontend_post_artifact_message() -> None:
    source = DASHBOARD_PATH.read_text(encoding='utf-8')
    if 'result.post_artifact_text' not in source and 'result.postArtifactText' not in source:
        return

    pattern = re.compile(
        r'(?P<indent>[ \t]*)setMessages\(\(current\) => \{\s*'
        r'const completed = current\.map\(\(message\) => \(.*?'
        r'const postText = String\(result\.post_artifact_text \|\| result\.postArtifactText \|\| [\'\"]{2}\)\.trim\(\);.*?'
        r'return \[\.\.\.completed, \{.*?\}\];\s*'
        r'\}\);',
        flags=re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        raise RuntimeError('Bloco de segunda mensagem posterior não localizado no Dashboard.jsx.')

    indent = match.group('indent')
    replacement = f'''{indent}setMessages((current) => current.map((message) => (
{indent}  message.taskId === taskId && message.role === 'assistant'
{indent}    ? {{
{indent}        ...message,
{indent}        text: result.reply || 'O DomnAI não retornou uma resposta em texto.',
{indent}        attachments: artifacts,
{indent}        processing: false,
{indent}        isError: false,
{indent}      }}
{indent}    : message
{indent})));'''
    source = source[:match.start()] + replacement + source[match.end():]

    if 'result.post_artifact_text' in source or 'result.postArtifactText' in source:
        raise RuntimeError('A segunda mensagem posterior permaneceu no frontend.')
    DASHBOARD_PATH.write_text(source, encoding='utf-8')


if ARTIFACT_DECISION_PATH.exists():
    patch_artifact_source_selection()
    remove_backend_post_artifact_messages()

if DASHBOARD_PATH.exists():
    remove_frontend_post_artifact_message()

print('Entrega de artefato finalizada: conteúdo útil preservado e somente uma mensagem junto ao arquivo.')
