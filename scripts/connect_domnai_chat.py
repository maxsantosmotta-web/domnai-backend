from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

source = source.replace(
    "import React, { useMemo, useRef, useState } from 'react';",
    "import React, { useEffect, useMemo, useRef, useState } from 'react';",
    1,
)
source = source.replace(
    "import './dashboard-adjustments.css';",
    "import './dashboard-adjustments.css';\nimport './dashboard-operation-blocks.css';",
    1,
)
source = source.replace(
    "  const { getToken } = useAuth();",
    "  const { getToken, userId } = useAuth();",
    1,
)

if "const pollingTasksRef" not in source:
    source = source.replace(
        "  const fileInputRef = useRef(null);",
        "  const fileInputRef = useRef(null);\n  const pollingTasksRef = useRef(new Set());",
        1,
    )

if "const [responding, setResponding]" not in source:
    source = source.replace(
        "  const [uploading, setUploading] = useState(false);",
        "  const [uploading, setUploading] = useState(false);\n  const [responding, setResponding] = useState(false);",
        1,
    )

if "const [conversationReady, setConversationReady]" not in source:
    source = source.replace(
        "  const [responding, setResponding] = useState(false);",
        "  const [responding, setResponding] = useState(false);\n  const [conversationReady, setConversationReady] = useState(false);",
        1,
    )

polling_block = '''
  async function pollChatTask(taskId) {
    if (!taskId || pollingTasksRef.current.has(taskId)) return;
    pollingTasksRef.current.add(taskId);
    setResponding(true);

    try {
      for (let attempt = 0; attempt < 240; attempt += 1) {
        const response = await authorizedFetch(`/api/chat/tasks/${taskId}`);
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || 'Não foi possível acompanhar a resposta do DomnAI.');

        if (payload.status === 'completed') {
          const result = payload.result || {};
          const artifacts = result.artifacts || [];
          setMessages((current) => current.map((message) => (
            message.taskId === taskId && message.role === 'assistant'
              ? {
                  ...message,
                  text: result.reply || 'O DomnAI não retornou uma resposta em texto.',
                  attachments: artifacts,
                  processing: false,
                  isError: false,
                }
              : message
          )));
          return;
        }

        if (payload.status === 'failed') {
          setMessages((current) => current.map((message) => (
            message.taskId === taskId && message.role === 'assistant'
              ? {
                  ...message,
                  text: payload.error || 'Não foi possível concluir a resposta.',
                  processing: false,
                  isError: true,
                }
              : message
          )));
          return;
        }

        await new Promise((resolve) => window.setTimeout(resolve, 1200));
      }

      setMessages((current) => current.map((message) => (
        message.taskId === taskId && message.role === 'assistant'
          ? {
              ...message,
              text: 'A resposta continua sendo processada. Ela será restaurada quando você voltar.',
              processing: true,
              isError: false,
            }
          : message
      )));
    } catch (error) {
      setMessages((current) => current.map((message) => (
        message.taskId === taskId && message.role === 'assistant'
          ? {
              ...message,
              text: error.message || 'Não foi possível acompanhar a resposta.',
              processing: false,
              isError: true,
            }
          : message
      )));
    } finally {
      pollingTasksRef.current.delete(taskId);
      setResponding(false);
    }
  }

'''

if "async function pollChatTask(taskId)" not in source:
    marker = "  async function buildImagePreviewMap(items, basePath) {"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o ponto de inserção do polling.')
    source = source.replace(marker, polling_block + marker, 1)

persistence_block = '''
  useEffect(() => {
    if (!userId) return undefined;
    let cancelled = false;
    setConversationReady(false);

    authorizedFetch('/api/chat-state')
      .then(async (response) => {
        if (!response.ok) throw new Error('Não foi possível restaurar a conversa.');
        return response.json();
      })
      .then((payload) => {
        if (cancelled) return;
        const restoredMessages = Array.isArray(payload.messages) ? payload.messages : [];
        setMessages(restoredMessages);
        setActiveOperation(payload.activeOperation || null);
        setConversationReady(true);
        const pendingTasks = restoredMessages.filter(
          (message) => message.role === 'assistant' && message.processing && message.taskId,
        );
        if (pendingTasks.length) setResponding(true);
        pendingTasks.forEach((message) => pollChatTask(message.taskId));
      })
      .catch(() => {
        if (!cancelled) setConversationReady(true);
      });

    return () => { cancelled = true; };
  }, [userId]);

  useEffect(() => {
    if (!userId || !conversationReady) return undefined;
    const timer = window.setTimeout(() => {
      const serializableMessages = messages.map((message) => ({
        id: message.id,
        role: message.role,
        text: message.text || '',
        operationId: message.operationId || null,
        isError: Boolean(message.isError),
        taskId: message.taskId || null,
        processing: Boolean(message.processing),
        attachments: (message.attachments || []).map((item) => ({
          id: item.id,
          libraryId: item.libraryId || null,
          name: item.name,
          type: item.type,
          mimeType: item.mimeType || '',
          size: item.size || item.sizeBytes || 0,
        })),
      }));

      authorizedFetch('/api/chat-state', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: serializableMessages,
          active_operation: activeOperation,
        }),
      }).catch(() => {});
    }, 250);

    return () => window.clearTimeout(timer);
  }, [messages, activeOperation, conversationReady, userId]);

'''

if "authorizedFetch('/api/chat-state')" not in source:
    source = source.replace(
        "  const showExitButton = section !== 'chat';\n",
        persistence_block + "  const showExitButton = section !== 'chat';\n",
        1,
    )

select_operation_block = '''  function selectOperation(item) {
    if (responding) return;

    setActiveOperation(item.id);
    setSection('chat');
    setDraft(item.name);
    setAttachments([]);
    setPlusOpen(false);
    setSidebarOpen(false);
  }
'''

source, operation_count = re.subn(
    r"  (?:async )?function selectOperation\(item\) \{.*?\n  \}",
    select_operation_block.rstrip(),
    source,
    count=1,
    flags=re.S,
)
if operation_count != 1:
    raise RuntimeError('Não foi possível localizar selectOperation em Dashboard.jsx.')

send_block = '''  async function sendMessage(event) {
    event.preventDefault();
    const text = draft.trim();
    if ((!text && attachments.length === 0) || uploading || responding) return;

    const sentAttachments = [...attachments];
    const localMessageId = Date.now();
    const userMessage = {
      id: localMessageId,
      role: 'user',
      text,
      attachments: sentAttachments,
      processing: false,
    };

    const lastOperationIndex = messages.reduce(
      (lastIndex, message, index) => message.role === 'operation' ? index : lastIndex,
      -1,
    );
    const currentBlockMessages = lastOperationIndex >= 0 ? messages.slice(lastOperationIndex + 1) : messages;
    const history = currentBlockMessages
      .filter((message) => ['user', 'assistant'].includes(message.role) && message.text?.trim() && !message.processing)
      .slice(-40)
      .map((message) => ({ role: message.role, content: message.text.trim() }));

    const operationName = operations.find((item) => item.id === activeOperation)?.name || null;
    const messageForApi = text || `Analise os arquivos anexados: ${sentAttachments.map((item) => item.name).join(', ')}`;

    setMessages((current) => [...current, userMessage]);
    setDraft('');
    setAttachments([]);
    setPlusOpen(false);
    setResponding(true);

    try {
      const response = await authorizedFetch('/api/chat/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageForApi,
          operation: operationName,
          history,
          attachments: sentAttachments
            .filter((item) => item.libraryId)
            .map((item) => ({ library_id: item.libraryId })),
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível iniciar a resposta do DomnAI.');

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
        text: error.message || 'Não foi possível concluir a análise. Tente novamente.',
        attachments: [],
        isError: true,
        processing: false,
      }]);
      setResponding(false);
    }
  }

'''

source, count = re.subn(
    r"  (?:async )?function sendMessage\(event\) \{.*?\n  \}\n\n(?=  async function moveLibraryAssetToTrash)",
    send_block,
    source,
    count=1,
    flags=re.S,
)
if count != 1 and "async function sendMessage(event)" not in source:
    raise RuntimeError('Não foi possível localizar sendMessage em Dashboard.jsx.')

operation_render = '''{visibleMessages.map((message) => message.role === 'operation' ? (
                <div className="chat-operation-divider" key={message.id} data-operation-id={message.operationId || ''}>
                  <span>Nova operação</span>
                  {message.text ? <strong>{message.text}</strong> : null}
                </div>
              ) : (
                <article className={`chat-message ${message.role}${message.isError ? ' error' : ''}`} key={message.id}>
                  <span className="message-author">{message.role === 'assistant' ? 'DomnAI' : 'Você'}</span>
                  {message.text ? <p>{message.text}</p> : null}
                  {(message.attachments || []).length ? <div className="message-attachments">{message.attachments.map((item) => item.type === 'image' && item.previewUrl ? <figure className="chat-image-native" key={item.id}><img src={item.previewUrl} alt={item.name} /><figcaption><span>{item.name}</span><div><button type="button" onClick={() => openAttachment(item)}>Abrir imagem</button><button type="button" className="danger" onClick={() => deleteAttachment(item)}>Excluir</button></div></figcaption></figure> : <div className="chat-native-file" key={item.id}>{renderNativeFile(item, () => openAttachment(item))}<button type="button" className="native-delete-button" onClick={() => deleteAttachment(item)}>Excluir</button></div>)}</div> : null}
                </article>
              ))}'''

render_start = source.find("{visibleMessages.map((message) =>")
render_end_marker = "            </div>\n            <form className=\"chat-composer simplified-composer composer-with-plus\" onSubmit={sendMessage}>"
render_end = source.find(render_end_marker, render_start)
if render_start == -1 or render_end == -1:
    raise RuntimeError('Não foi possível localizar a renderização das mensagens.')
source = source[:render_start] + operation_render + "\n" + source[render_end:]

source = source.replace(
    "placeholder={uploading ? 'Salvando na biblioteca...' : 'Digite sua mensagem...'} rows=\"3\" disabled={uploading} /><button type=\"submit\" className=\"send-message-button\" aria-label=\"Enviar mensagem\" disabled={uploading}>➤</button>",
    "placeholder={uploading ? 'Salvando na biblioteca...' : responding ? 'Aguarde a resposta do DomnAI...' : 'Digite sua mensagem...'} rows=\"3\" disabled={uploading || responding} /><button type=\"submit\" className=\"send-message-button\" aria-label=\"Enviar mensagem\" disabled={uploading || responding}>➤</button>",
    1,
)

path.write_text(source, encoding='utf-8')
