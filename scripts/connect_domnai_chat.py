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
        setMessages(Array.isArray(payload.messages) ? payload.messages : []);
        setActiveOperation(payload.activeOperation || null);
        setConversationReady(true);
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

select_operation_block = '''  async function selectOperation(item) {
    if (responding) return;

    const lastMessage = messages[messages.length - 1];
    const alreadyCurrent = activeOperation === item.id && lastMessage?.role === 'operation';

    setActiveOperation(item.id);
    setSection('chat');
    setDraft('');
    setAttachments([]);
    setPlusOpen(false);
    setSidebarOpen(false);

    if (alreadyCurrent) return;

    const operationDivider = {
      id: `operation-${item.id}-${Date.now()}`,
      role: 'operation',
      text: item.name,
      operationId: item.id,
      attachments: [],
    };

    setMessages((current) => [...current, operationDivider]);
    setResponding(true);

    try {
      const response = await authorizedFetch('/api/chat/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: 'Inicie esta operação agora. Faça somente a primeira pergunta necessária para conduzir o usuário, de forma objetiva e sem pedir que ele explique o nome da operação. Quando a operação depender de arquivo, imagem, contrato, orçamento, anúncio ou documento, peça diretamente que o usuário envie o material adequado.',
          operation: item.name,
          history: [],
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível iniciar esta operação.');

      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: 'assistant',
        text: payload.reply || 'Envie as informações ou arquivos necessários para começarmos.',
        attachments: [],
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: 'assistant',
        text: error.message || 'Não foi possível iniciar esta operação. Tente novamente.',
        attachments: [],
        isError: true,
      }]);
    } finally {
      setResponding(false);
    }
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
    const userMessage = {
      id: Date.now(),
      role: 'user',
      text,
      attachments: sentAttachments,
    };

    const lastOperationIndex = messages.reduce(
      (lastIndex, message, index) => message.role === 'operation' ? index : lastIndex,
      -1,
    );
    const currentBlockMessages = lastOperationIndex >= 0 ? messages.slice(lastOperationIndex + 1) : messages;
    const history = currentBlockMessages
      .filter((message) => ['user', 'assistant'].includes(message.role) && message.text?.trim())
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
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || 'Não foi possível obter a resposta do DomnAI.');
      }
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: 'assistant',
        text: payload.reply || 'O DomnAI não retornou uma resposta em texto.',
        attachments: [],
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: 'assistant',
        text: error.message || 'Não foi possível concluir a análise. Tente novamente.',
        attachments: [],
        isError: true,
      }]);
    } finally {
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
                  <strong>{message.text}</strong>
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

analyzing = "              {responding ? <article className=\"chat-message assistant analyzing\"><span className=\"message-author\">DomnAI</span><p>DomnAI está analisando...</p></article> : null}"
if analyzing not in source:
    target = "            </div>\n            <form className=\"chat-composer simplified-composer composer-with-plus\" onSubmit={sendMessage}>"
    replacement = f"{analyzing}\n            </div>\n            <form className=\"chat-composer simplified-composer composer-with-plus\" onSubmit={{sendMessage}}>"
    if target not in source:
        raise RuntimeError('Não foi possível localizar o compositor do chat.')
    source = source.replace(target, replacement, 1)

source = source.replace(
    "placeholder={uploading ? 'Salvando na biblioteca...' : 'Digite sua mensagem...'} rows=\"3\" disabled={uploading} /><button type=\"submit\" className=\"send-message-button\" aria-label=\"Enviar mensagem\" disabled={uploading}>➤</button>",
    "placeholder={uploading ? 'Salvando na biblioteca...' : responding ? 'Aguarde a resposta do DomnAI...' : 'Digite sua mensagem...'} rows=\"3\" disabled={uploading || responding} /><button type=\"submit\" className=\"send-message-button\" aria-label=\"Enviar mensagem\" disabled={uploading || responding}>➤</button>",
    1,
)

path.write_text(source, encoding='utf-8')
