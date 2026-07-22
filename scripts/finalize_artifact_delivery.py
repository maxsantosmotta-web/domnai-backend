from pathlib import Path
import ast

# Escopo fechado: entrega pendente, decisão delegada, remoção de contradições e finalização premium.


def _extend_named_collection(source: str, name: str, values: tuple[str, ...]) -> str:
    """Atualiza set/tuple pelo AST, sem depender da formatação textual do arquivo."""
    tree = ast.parse(source)
    target_node = None
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            target_node = node
            break
    if target_node is None or not hasattr(target_node, "end_lineno"):
        raise RuntimeError(f'Coleção {name} não encontrada no decisor de artefatos.')

    literal_text = ast.get_source_segment(source, target_node.value)
    try:
        current = ast.literal_eval(literal_text)
    except (ValueError, SyntaxError) as exc:
        raise RuntimeError(f'Coleção {name} não pôde ser interpretada com segurança.') from exc

    if isinstance(current, set):
        merged = sorted(set(current).union(values))
        replacement = name + " = {\n" + "".join(f"    {item!r},\n" for item in merged) + "}"
    elif isinstance(current, tuple):
        merged = list(dict.fromkeys([*current, *values]))
        replacement = name + " = (\n" + "".join(f"    {item!r},\n" for item in merged) + ")"
    else:
        raise RuntimeError(f'Coleção {name} precisa ser set ou tuple.')

    lines = source.splitlines(keepends=True)
    start = target_node.lineno - 1
    end = target_node.end_lineno
    suffix = "\n" if lines[end - 1].endswith("\n") else ""
    lines[start:end] = [replacement + suffix]
    updated = "".join(lines)
    compile(updated, 'artifact_decision.py', 'exec')
    return updated


# 1) Aceitar delegação natural do usuário como autorização para concluir o arquivo oferecido.
decision_path = Path('/app/app/services/artifact_decision.py')
decision = decision_path.read_text(encoding='utf-8')
decision = _extend_named_collection(
    decision,
    '_ACCEPTANCE_EXACT',
    (
        'voce decide',
        'você decide',
        'pode escolher',
        'como achar melhor',
        'como voce achar melhor',
        'como você achar melhor',
    ),
)
decision = _extend_named_collection(
    decision,
    '_ACCEPTANCE_PHRASES',
    (
        'voce decide',
        'você decide',
        'pode escolher',
        'escolha voce',
        'escolha você',
        'como achar melhor',
        'como voce achar melhor',
        'como você achar melhor',
        'da forma que achar melhor',
        'do jeito que achar melhor',
    ),
)
decision_path.write_text(decision, encoding='utf-8')

# 2) Registrar estado real de entrega pendente no payload da tarefa.
persistent_path = Path('/app/app/api/chat_persistent.py')
persistent = persistent_path.read_text(encoding='utf-8')

old_resolution = '''    history = [item.model_dump() for item in payload.history]
    local_artifact_followup = resolve_local_artifact_request(message, history) is not None
    if not local_artifact_followup:
        ensure_minimum_credit(user_id)
'''
new_resolution = '''    history = [item.model_dump() for item in payload.history]
    pending_artifact = resolve_local_artifact_request(message, history)
    local_artifact_followup = pending_artifact is not None
    artifact_delivery_state = "pending" if local_artifact_followup else None
    if not local_artifact_followup:
        ensure_minimum_credit(user_id)
'''
if old_resolution in persistent:
    persistent = persistent.replace(old_resolution, new_resolution, 1)
elif 'artifact_delivery_state = "pending"' not in persistent:
    raise RuntimeError('Resolução de artefato pendente não encontrada no chat persistente.')

old_payload = '''                "attachment_ids": attachment_ids,
                "local_artifact_followup": local_artifact_followup,
'''
new_payload = '''                "attachment_ids": attachment_ids,
                "local_artifact_followup": local_artifact_followup,
                "artifact_delivery_state": artifact_delivery_state,
                "pending_artifact": pending_artifact,
'''
if old_payload in persistent:
    persistent = persistent.replace(old_payload, new_payload, 1)
elif '"pending_artifact": pending_artifact' not in persistent:
    raise RuntimeError('Payload da tarefa não encontrado para registrar entrega pendente.')

persistent_path.write_text(persistent, encoding='utf-8')

# 3) Garantir que uma entrega pendente seja concluída antes de qualquer encerramento.
worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')

helper_marker = '''def _elapsed_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))
'''
helper = '''def _elapsed_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))


def _clean_artifact_contradictions(text: str) -> str:
    paragraphs = [part.strip() for part in str(text or "").split("\\n\\n") if part.strip()]
    blocked = (
        "nao consigo enviar arquivos", "não consigo enviar arquivos",
        "nao posso enviar arquivos", "não posso enviar arquivos",
        "nao consigo anexar arquivos", "não consigo anexar arquivos",
        "nao posso anexar arquivos", "não posso anexar arquivos",
        "nao consigo gerar arquivos", "não consigo gerar arquivos",
        "nao consigo enviar o arquivo", "não consigo enviar o arquivo",
        "nao posso enviar o arquivo", "não posso enviar o arquivo",
        "quer que eu organize", "deseja que eu organize",
        "quer que eu gere", "deseja que eu gere",
        "quer que eu crie", "deseja que eu crie",
    )
    kept = [part for part in paragraphs if not any(marker in part.casefold() for marker in blocked)]
    return "\\n\\n".join(kept).strip()


def _artifact_completion_message(artifact_type: str | None) -> str:
    return (
        "Pronto! Seu arquivo foi gerado com base nas informações desta conversa e está disponível logo abaixo. "
        "O conteúdo foi organizado para facilitar a leitura e a consulta. "
        "Ele também foi salvo automaticamente na Biblioteca.\\n\\n"
        "Importante: Este documento tem finalidade informativa e foi elaborado com base nas informações fornecidas "
        "durante esta conversa. Para decisões definitivas, recomenda-se sempre a validação por um profissional habilitado."
    )
'''
if '_clean_artifact_contradictions' not in worker:
    if helper_marker not in worker:
        raise RuntimeError('Ponto de inserção da finalização de artefatos não encontrado.')
    worker = worker.replace(helper_marker, helper, 1)

# A decisão registrada como pendente tem prioridade sobre qualquer desvio textual do modelo.
decision_marker = '''        decision = decide_artifact(
            message=original_message,
            operation=operation,
            history=history,
            answer=reply,
        )
'''
decision_replacement = '''        decision = decide_artifact(
            message=original_message,
            operation=operation,
            history=history,
            answer=reply,
        )
        pending_artifact = payload.get("pending_artifact")
        if payload.get("artifact_delivery_state") == "pending" and isinstance(pending_artifact, dict):
            decision = pending_artifact
'''
if decision_marker in worker:
    worker = worker.replace(decision_marker, decision_replacement, 1)
elif 'payload.get("artifact_delivery_state") == "pending"' not in worker:
    raise RuntimeError('Decisão de artefato não encontrada para priorizar entrega pendente.')

old_success = '''                artifacts.append(artifact)
                if result.provider == "local-artifact":
                    reply = "PDF criado e enviado aqui no chat. O mesmo arquivo também foi salvo automaticamente na Biblioteca."
                else:
                    reply = f"{reply.rstrip()}\\n\\nArquivo criado e enviado aqui no chat."'''
new_success = '''                artifacts.append(artifact)
                clean_reply = _clean_artifact_contradictions(reply)
                completion = _artifact_completion_message(decision.get("artifact_type"))
                reply = f"{clean_reply}\\n\\n{completion}" if clean_reply and result.provider != "local-artifact" else completion
                payload["artifact_delivery_state"] = "completed"'''
if old_success in worker:
    worker = worker.replace(old_success, new_success, 1)
elif 'payload["artifact_delivery_state"] = "completed"' not in worker:
    raise RuntimeError('Bloco de sucesso da geração de arquivo não encontrado.')

worker_path.write_text(worker, encoding='utf-8')

# 4) Regra geral restrita à entrega: não encerrar antes de cumprir uma promessa de arquivo.
prompt_path = Path('/app/app/services/domnai_brain.py')
prompt = prompt_path.read_text(encoding='utf-8')
anchor = '20. Nunca afirme que criou, enviou ou compartilhou e-mail, planilha, arquivo ou link externo sem confirmação técnica.\n'
rule = (
    '20. Quando o usuário aceitar ou delegar a criação de PDF, planilha ou arquivo, trate isso como autorização para '
    'concluir a entrega imediatamente. Não faça nova pergunta sobre formato quando o melhor formato puder ser inferido. '
    'Enquanto a entrega estiver pendente, não encerre o atendimento, não se despeça e não diga que ficará à disposição. '
    'Somente confirme a conclusão depois que o arquivo tiver sido realmente criado e apresentado.\n'
)
if 'Enquanto a entrega estiver pendente' not in prompt:
    if anchor not in prompt:
        raise RuntimeError('Regra de confirmação técnica não encontrada no prompt central.')
    prompt = prompt.replace(anchor, rule + anchor, 1)

prompt_path.write_text(prompt, encoding='utf-8')
