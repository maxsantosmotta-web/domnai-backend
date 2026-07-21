from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path('/app/app/services')


def read(name: str) -> str:
    path = ROOT / name
    text = path.read_text(encoding='utf-8')
    ast.parse(text, filename=str(path))
    return text


def function_keywords(tree: ast.AST, function_name: str) -> set[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return {arg.arg for arg in node.args.args + node.args.kwonlyargs}
    raise RuntimeError(f'função ausente: {function_name}')


def call_keywords(tree: ast.AST, function_name: str) -> list[set[str]]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == function_name:
            found.append({item.arg for item in node.keywords if item.arg})
    return found


worker = read('chat_task_worker.py')
orchestrator = read('orchestrated_brain.py')
planner = read('intelligence_orchestrator.py')
memory = read('diagnosis_memory.py')
research = read('web_research.py')
worker_tree = ast.parse(worker)
orchestrator_tree = ast.parse(orchestrator)

required_worker = (
    'processing_for_same_user',
    'should_research_web(original_message)',
    'message=original_message',
    'history=contextual_history',
    'EVIDÊNCIA EXTERNA VERIFICADA (não é fala do usuário)',
    'CONTEXTO INTERNO SEPARADO DA MENSAGEM DO USUÁRIO',
)
for marker in required_worker:
    if marker not in worker:
        raise RuntimeError(f'worker sem propriedade obrigatória: {marker}')

for forbidden in (
    'should_research_web(original_message, operation)',
    'message=message_for_brain',
    'external_context=external_context',
    'PESQUISA WEB VERIFICADA:\n{research.text}',
):
    if forbidden in worker:
        raise RuntimeError(f'worker ainda contém comportamento antigo: {forbidden}')

accepted = function_keywords(orchestrator_tree, 'generate_orchestrated_response')
calls = call_keywords(worker_tree, 'generate_orchestrated_response')
if not calls:
    raise RuntimeError('worker não chama generate_orchestrated_response')
for keywords in calls:
    unexpected = keywords - accepted
    if unexpected:
        raise RuntimeError(f'chamada incompatível com generate_orchestrated_response: {sorted(unexpected)}')

required_orchestrator = (
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

print('Regressão do runtime e compatibilidade de assinatura validadas com sucesso.')
