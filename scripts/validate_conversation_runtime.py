from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path('/app/app/services')


def read(name: str) -> str:
    path = ROOT / name
    text = path.read_text(encoding='utf-8')
    ast.parse(text, filename=str(path))
    return text


worker = read('chat_task_worker.py')
orchestrator = read('orchestrated_brain.py')
planner = read('intelligence_orchestrator.py')
memory = read('diagnosis_memory.py')
research = read('web_research.py')

required_worker = (
    'processing_for_same_user',
    'should_research_web(original_message)',
    'message=original_message',
    'external_context=external_context',
    'EVIDÊNCIA EXTERNA VERIFICADA (não é fala do usuário)',
)
for marker in required_worker:
    if marker not in worker:
        raise RuntimeError(f'worker sem propriedade obrigatória: {marker}')

for forbidden in (
    'should_research_web(original_message, operation)',
    'message=message_for_brain',
    'PESQUISA WEB VERIFICADA:\n{research.text}',
):
    if forbidden in worker:
        raise RuntimeError(f'worker ainda contém comportamento antigo: {forbidden}')

required_orchestrator = (
    'external_context: str = ""',
    'contextual_history = list(history)',
    'history=_normalized_history(contextual_history)',
    'history=contextual_history',
    'operation=None,',
    'del operation',
)
for marker in required_orchestrator:
    if marker not in orchestrator:
        raise RuntimeError(f'orquestrador sem propriedade obrigatória: {marker}')

for forbidden in (
    'if operation_text == labor_operation:',
    'if _is_explicit_topic_switch(message):',
    'if _specialized_engine({}, operation, message) is None:',
):
    if forbidden in orchestrator:
        raise RuntimeError(f'orquestrador ainda contém regra antiga: {forbidden}')

required_planner = (
    'A operação ativa é apenas uma preferência visual',
    'A mensagem atual tem prioridade sobre histórico, memória e operação',
    'Sofrimento emocional e possível risco à vida têm prioridade absoluta',
    'nunca aceite precisão sem evidência',
)
for marker in required_planner:
    if marker not in planner:
        raise RuntimeError(f'planejador sem política global: {marker}')

required_memory = (
    '"operation": None,',
    'ela nunca decide a intenção da mensagem atual',
    'Mudança real de assunto interrompe o foco anterior',
)
for marker in required_memory:
    if marker not in memory:
        raise RuntimeError(f'memória sem neutralidade obrigatória: {marker}')

if 'text = f"{operation or \'\'} {message or \'\'}".casefold()' in research:
    raise RuntimeError('pesquisa web ainda depende da operação visual')

print('Regressão do runtime conversacional validada com sucesso.')
