from pathlib import Path
import re


# Corrige o fluxo de nova operação de forma atômica: o backend preserva e devolve
# o histórico já salvo com o divisor da nova operação, e o frontend usa exatamente
# essa resposta. Isso elimina corrida entre estado local e persistência automática.

frontend_path = Path('/frontend/src/Dashboard.jsx')
if frontend_path.exists():
    source = frontend_path.read_text(encoding='utf-8')
    replacement = '''  async function selectOperation(item) {
    if (responding) return;

    try {
      const response = await authorizedFetch('/api/chat-state/new-operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active_operation: item.id, operation_name: item.name }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || 'Não foi possível iniciar uma nova operação.');
      }

      setMessages(Array.isArray(payload.messages) ? payload.messages : []);
      setActiveOperation(payload.activeOperation || item.id);
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
    } catch (error) {
      window.alert(error.message || 'Não foi possível iniciar uma nova operação.');
    }
  }'''
    source, count = re.subn(
        r"  (?:async )?function selectOperation\(item\) \{.*?\n  \}",
        replacement,
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError('Frontend: seleção de operação não encontrada para correção atômica.')
    frontend_path.write_text(source, encoding='utf-8')
    print('Frontend: nova operação passou a usar o histórico retornado pelo servidor.')


backend_path = Path('/app/app/api/chat_state.py')
if backend_path.exists():
    source = backend_path.read_text(encoding='utf-8')

    source = source.replace(
        '''class NewOperationPayload(BaseModel):
    active_operation: str = Field(min_length=1, max_length=120)
''',
        '''class NewOperationPayload(BaseModel):
    active_operation: str = Field(min_length=1, max_length=120)
    operation_name: str = Field(min_length=1, max_length=180)
''',
        1,
    )

    endpoint = '''@router.post("/new-operation")
def start_new_operation(payload: NewOperationPayload, session: dict = Depends(require_authenticated_user)):
    user_id = _user_id(session)
    clear_diagnosis_state(user_id)
    with session_scope() as db:
        state = db.get(ActiveChatState, user_id)
        if state is None:
            state = ActiveChatState(user_id=user_id, messages_json="[]")
            db.add(state)

        messages = _load_messages(state)
        divider = {
            "id": f"operation-{state.updated_at.timestamp() if state.updated_at else 0}-{len(messages)}",
            "role": "operation",
            "text": payload.operation_name,
            "operationId": payload.active_operation,
            "attachments": [],
            "sources": [],
            "isError": False,
            "taskId": None,
            "processing": False,
        }
        messages.append(divider)
        state.messages_json = json.dumps(messages[-300:], ensure_ascii=False)
        state.active_operation = payload.active_operation
        db.flush()
        return {
            "started": True,
            "activeOperation": payload.active_operation,
            "messages": messages[-300:],
        }
'''

    source, count = re.subn(
        r'@router\.post\("/new-operation"\)\ndef start_new_operation\(payload: NewOperationPayload, session: dict = Depends\(require_authenticated_user\)\):.*?\n\s*return \{.*?\}\n',
        endpoint,
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError('Backend: endpoint de nova operação não encontrado para correção atômica.')

    backend_path.write_text(source, encoding='utf-8')
    print('Backend: nova operação agora preserva e retorna o histórico de forma atômica.')
