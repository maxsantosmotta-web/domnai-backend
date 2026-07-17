from pathlib import Path
import re


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    if old not in source:
        raise RuntimeError(f"{label}: trecho esperado não encontrado")
    return source.replace(old, new, 1)


# FRONTEND: iniciar um novo bloco contextual sem apagar o histórico visual/persistido.
frontend_path = Path('/frontend/src/Dashboard.jsx')
if frontend_path.exists():
    source = frontend_path.read_text(encoding='utf-8')
    replacement = '''  async function selectOperation(item) {
    if (responding) return;

    try {
      const response = await authorizedFetch('/api/chat-state/new-operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active_operation: item.id }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || 'Não foi possível iniciar uma nova operação.');
      }
    } catch (error) {
      window.alert(error.message || 'Não foi possível iniciar uma nova operação.');
      return;
    }

    const divider = {
      id: `operation-${Date.now()}`,
      role: 'operation',
      text: item.name,
      operationId: item.id,
      attachments: [],
      sources: [],
      processing: false,
      isError: false,
    };
    setMessages((current) => [...current, divider]);
    setActiveOperation(item.id);
    setSection('chat');
    setAttachments([]);
    setSearch('');
    setSearchOpen(false);
    setOptionsOpen(false);
    setPlusOpen(false);
    setSidebarOpen(false);

    window.setTimeout(() => {
      setDraft(item.name);
      setComposerScrollRequest((current) => current + 1);
    }, 240);
  }'''
    source, count = re.subn(
        r"  (?:async )?function selectOperation\(item\) \{.*?\n  \}",
        replacement,
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError('Frontend: seleção de operação não encontrada.')
    frontend_path.write_text(source, encoding='utf-8')
    print('Frontend: nova operação preserva o histórico e reinicia apenas o contexto.')


# BACKEND: endpoint para reiniciar apenas o contexto estruturado.
backend_root = Path('/app/app')
if backend_root.exists():
    state_path = backend_root / 'api' / 'chat_state.py'
    state = state_path.read_text(encoding='utf-8')
    payload_marker = '''class ChatStatePayload(BaseModel):
    messages: list[dict] = Field(default_factory=list, max_length=300)
    active_operation: str | None = Field(default=None, max_length=120)
'''
    payload_replacement = payload_marker + '''

class NewOperationPayload(BaseModel):
    active_operation: str = Field(min_length=1, max_length=120)
'''
    if 'class NewOperationPayload' not in state:
        state = replace_once(state, payload_marker, payload_replacement, 'Backend: payload de nova operação')

    endpoint = '''

@router.post("/new-operation")
def start_new_operation(payload: NewOperationPayload, session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    clear_diagnosis_state(user_id)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is None:
            state = ActiveChatState(user_id=user_id, messages_json="[]")
            db.add(state)
        state.active_operation = payload.active_operation
        db.flush()
    return {"started": True, "activeOperation": payload.active_operation}
'''
    if '@router.post("/new-operation")' not in state:
        marker = '\n\n@router.delete("")\n'
        if marker not in state:
            raise RuntimeError('Backend: ponto de inserção do reinício contextual não encontrado.')
        state = state.replace(marker, endpoint + marker, 1)
    state_path.write_text(state, encoding='utf-8')

    # Escolher a resposta analítica mais completa como fonte do PDF, nunca uma pergunta operacional.
    artifact_source_path = backend_root / 'services' / 'artifact_source.py'
    artifact_source = artifact_source_path.read_text(encoding='utf-8')
    artifact_source = artifact_source.replace(
        '''    "domnai esta analisando",
)''',
        '''    "domnai esta analisando",
    "informe seu e-mail",
    "informe seu email",
    "envio do pdf por e-mail",
    "envio do pdf por email",
)''',
        1,
    )
    old_source_function = '''def _last_substantive_assistant_answer(history: list[dict]) -> str:
    for item in reversed(history):
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        candidate = str(item.get("content") or "").strip()
        normalized = _normalize(candidate)
        if len(candidate) < 120:
            continue
        if any(marker in normalized for marker in _BLOCKED_SOURCE_MARKERS):
            continue
        return candidate
    return ""
'''
    new_source_function = '''def _last_substantive_assistant_answer(history: list[dict]) -> str:
    candidates: list[str] = []
    for item in history:
        if str(item.get("role") or "").strip().lower() != "assistant":
            continue
        candidate = str(item.get("content") or "").strip()
        normalized = _normalize(candidate)
        if len(candidate) < 120:
            continue
        if any(marker in normalized for marker in _BLOCKED_SOURCE_MARKERS):
            continue
        candidates.append(candidate)
    return max(candidates, key=len) if candidates else ""
'''
    if new_source_function not in artifact_source:
        artifact_source = replace_once(
            artifact_source,
            old_source_function,
            new_source_function,
            'Backend: fonte consolidada do PDF',
        )
    artifact_source_path.write_text(artifact_source, encoding='utf-8')

    # Entrega local de arquivo: não chamar o modelo novamente e não pedir e-mail.
    worker_path = backend_root / 'services' / 'chat_task_worker.py'
    worker = worker_path.read_text(encoding='utf-8')
    old_intelligence = '''        intelligence_started_at = time.perf_counter()
        result = generate_orchestrated_response(
            message=message_for_brain,
            operation=operation,
            history=history,
            attachments=attachments,
            diagnosis_state=diagnosis_state,
        )
        timings["intelligence_ms"] = _elapsed_ms(intelligence_started_at)
        timings.update(getattr(result, "timings", None) or {})
'''
    new_intelligence = '''        pending_artifact = payload.get("pending_artifact")
        pending_source = (
            str(pending_artifact.get("source_answer") or "").strip()
            if isinstance(pending_artifact, dict)
            else ""
        )
        if payload.get("artifact_delivery_state") == "pending" and len(pending_source) >= 120:
            from app.services.metered_brain import MeteredBrainResult
            result = MeteredBrainResult(
                text=pending_source,
                provider="local-artifact",
                model="local-artifact",
                input_tokens=0,
                output_tokens=0,
                cached_input_tokens=0,
                diagnosis_state=diagnosis_state,
            )
            timings["intelligence_ms"] = 0
        else:
            intelligence_started_at = time.perf_counter()
            result = generate_orchestrated_response(
                message=message_for_brain,
                operation=operation,
                history=history,
                attachments=attachments,
                diagnosis_state=diagnosis_state,
            )
            timings["intelligence_ms"] = _elapsed_ms(intelligence_started_at)
            timings.update(getattr(result, "timings", None) or {})
'''
    if new_intelligence not in worker:
        worker = replace_once(worker, old_intelligence, new_intelligence, 'Backend: entrega local sem nova pergunta')

    old_pending_override = '''        pending_artifact = payload.get("pending_artifact")
        if payload.get("artifact_delivery_state") == "pending" and isinstance(pending_artifact, dict):
            decision = pending_artifact
'''
    new_pending_override = '''        pending_artifact = payload.get("pending_artifact")
        if payload.get("artifact_delivery_state") == "pending" and isinstance(pending_artifact, dict):
            decision = dict(pending_artifact)
            if str(decision.get("title") or "").strip() in {"", "Documento DomnAI"} and operation:
                decision["title"] = f"Relatório - {operation}"
'''
    if new_pending_override not in worker:
        worker = replace_once(worker, old_pending_override, new_pending_override, 'Backend: título e fonte do PDF pendente')

    worker = worker.replace(
        '''        "nao posso enviar o arquivo", "não posso enviar o arquivo",
    )''',
        '''        "nao posso enviar o arquivo", "não posso enviar o arquivo",
        "informe seu e-mail", "informe seu email",
        "envio do pdf por e-mail", "envio do pdf por email",
    )''',
        1,
    )
    worker_path.write_text(worker, encoding='utf-8')

    # PDF: resumo curto e conteúdo integral somente uma vez na seção Resultado.
    chat_path = backend_root / 'api' / 'chat.py'
    chat = chat_path.read_text(encoding='utf-8')
    chat = chat.replace(
        '''                "summary": clean_answer,
                "sections": [{"title": "Resultado", "content": clean_answer}],''',
        '''                "summary": "Relatório elaborado com base nas informações e conclusões apresentadas na conversa.",
                "sections": [{"title": "Resultado", "content": clean_answer}],''',
        1,
    )
    chat_path.write_text(chat, encoding='utf-8')
    print('Backend: contexto reiniciado sem apagar histórico e PDF gerado com o conteúdo real da conversa.')
