from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

retry_function = r'''
  async function retryFailedMessage(messageId) {
    if (responding) return;

    const errorIndex = messages.findIndex((message) => message.id === messageId && message.role === 'assistant' && message.isError);
    if (errorIndex < 0) return;

    let userIndex = -1;
    for (let index = errorIndex - 1; index >= 0; index -= 1) {
      if (messages[index]?.role === 'user') {
        userIndex = index;
        break;
      }
      if (messages[index]?.role === 'operation') break;
    }
    if (userIndex < 0) return;

    const errorMessage = messages[errorIndex];
    const userMessage = messages[userIndex];
    const originalTaskId = errorMessage.taskId || userMessage.taskId || null;
    const messageForApi = String(userMessage.text || '').trim()
      || `Analise os arquivos anexados: ${(userMessage.attachments || []).map((item) => item.name).join(', ')}`;
    if (!messageForApi) return;

    const lastOperationIndex = messages
      .slice(0, userIndex)
      .reduce((lastIndex, message, index) => message.role === 'operation' ? index : lastIndex, -1);
    const historyStart = lastOperationIndex >= 0 ? lastOperationIndex + 1 : 0;
    const history = messages
      .slice(historyStart, userIndex)
      .filter((message) => ['user', 'assistant'].includes(message.role) && message.text?.trim() && !message.processing && !message.isError)
      .slice(-40)
      .map((message) => ({ role: message.role, content: message.text.trim() }));

    const operationName = operations.find((item) => item.id === activeOperation)?.name || null;
    setResponding(true);
    setMessages((current) => current.map((message) => (
      message.id === messageId
        ? {
            ...message,
            text: 'DomnAI está analisando...',
            attachments: [],
            taskId: originalTaskId,
            processing: true,
            isError: false,
          }
        : message
    )));

    try {
      const response = originalTaskId
        ? await authorizedFetch(`/api/chat/tasks/${originalTaskId}/retry`, { method: 'POST' })
        : await authorizedFetch('/api/chat/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: messageForApi,
              operation: operationName,
              history,
              attachments: (userMessage.attachments || [])
                .filter((item) => item.libraryId)
                .map((item) => ({ library_id: item.libraryId })),
            }),
          });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível tentar novamente.');

      const taskId = payload.taskId || originalTaskId;
      if (!taskId) throw new Error('A tarefa não foi preparada corretamente.');

      setMessages((current) => current.map((message) => (
        message.id === messageId ? { ...message, taskId } : message
      )));
      pollChatTask(taskId);
    } catch (error) {
      setMessages((current) => current.map((message) => (
        message.id === messageId
          ? {
              ...message,
              text: error.message || 'Não foi possível tentar novamente.',
              processing: false,
              isError: true,
              taskId: originalTaskId,
            }
          : message
      )));
      setResponding(false);
    }
  }

'''

if 'async function retryFailedMessage(messageId)' not in source:
    marker = '  async function moveLibraryAssetToTrash'
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o ponto de inserção da função de nova tentativa.')
    source = source.replace(marker, retry_function + marker, 1)

if 'className="chat-retry-button"' not in source:
    marker = "{message.text ? <p>{message.text}</p> : null}"
    retry_button = "{message.role === 'assistant' && message.isError ? <button type=\"button\" className=\"chat-retry-button\" onClick={() => retryFailedMessage(message.id)} title=\"Tentar novamente\" aria-label=\"Tentar novamente\" disabled={responding}><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7\" /></svg></button> : null}"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar a mensagem para adicionar o botão de nova tentativa.')
    source = source.replace(marker, f"{marker}\n                   {retry_button}", 1)

path.write_text(source, encoding='utf-8')
