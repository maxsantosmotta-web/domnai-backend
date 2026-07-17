from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

replacement = '''  async function selectOperation(item) {
    if (responding) return;

    setResponding(true);
    setDraft('');
    setAttachments([]);
    setSearch('');
    setSearchOpen(false);
    setOptionsOpen(false);
    setPlusOpen(false);
    setSidebarOpen(false);
    setSection('chat');

    try {
      const stateResponse = await authorizedFetch('/api/chat-state/new-operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active_operation: item.id, operation_name: item.name }),
      });
      const statePayload = await stateResponse.json().catch(() => ({}));
      if (!stateResponse.ok) {
        throw new Error(statePayload.detail || 'Não foi possível iniciar uma nova operação.');
      }

      const baseMessages = Array.isArray(statePayload.messages) ? statePayload.messages : [];
      const localMessageId = Date.now();
      const userMessage = {
        id: localMessageId,
        role: 'user',
        text: item.name,
        attachments: [],
        processing: false,
      };

      setActiveOperation(statePayload.activeOperation || item.id);
      setMessages([...baseMessages, userMessage]);

      const response = await authorizedFetch('/api/chat/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: item.name,
          operation: item.name,
          history: [],
          attachments: [],
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || 'Não foi possível iniciar a resposta do DomnAI.');
      }

      const taskId = payload.taskId;
      if (!taskId) throw new Error('A tarefa persistente não foi criada corretamente.');

      setMessages((current) => [
        ...current.map((message) => (
          message.id === localMessageId ? { ...message, taskId } : message
        )),
        {
          id: `assistant-${taskId}`,
          role: 'assistant',
          text: 'DomnAI está analisando...',
          attachments: [],
          taskId,
          processing: true,
          isError: false,
        },
      ]);
      pollChatTask(taskId);
    } catch (error) {
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: 'assistant',
        text: error.message || 'Não foi possível iniciar a operação. Tente novamente.',
        attachments: [],
        isError: true,
        processing: false,
      }]);
      setResponding(false);
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
    raise RuntimeError('Não foi possível localizar selectOperation para corrigir o clique único.')

path.write_text(source, encoding='utf-8')
print('Operação agora inicia com um único clique, sem duplicar conteúdo no campo de mensagem.')
