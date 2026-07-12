from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

source = source.replace(
    "import './dashboard-operation-blocks.css';",
    "import './dashboard-operation-blocks.css';\nimport './dashboard-delete-modal.css';",
    1,
)

source = source.replace(
    "  const fileInputRef = useRef(null);",
    "  const fileInputRef = useRef(null);\n  const longPressTimerRef = useRef(null);",
    1,
)

source = source.replace(
    "  const [conversationReady, setConversationReady] = useState(false);",
    "  const [conversationReady, setConversationReady] = useState(false);\n  const [pendingDelete, setPendingDelete] = useState(null);",
    1,
)

helpers = '''
  function removeAttachmentFromChat(item) {
    setAttachments((current) => current.filter((entry) => entry.id !== item.id));
    setMessages((current) => current
      .map((message) => ({
        ...message,
        attachments: (message.attachments || []).filter((entry) => entry.id !== item.id),
      }))
      .filter((message) => message.role === 'operation' || keepMessage(message)));
  }

  function deleteChatMessage(messageId) {
    setMessages((current) => current.filter((message) => message.id !== messageId));
  }

  function confirmDeleteMessage(messageId) {
    setPendingDelete({ type: 'message', messageId });
  }

  function confirmDeleteAttachment(item) {
    setPendingDelete({ type: 'attachment', item });
  }

  function confirmDeleteConversation() {
    setPendingDelete({ type: 'conversation' });
    setOptionsOpen(false);
  }

  function executePendingDelete() {
    if (!pendingDelete) return;

    if (pendingDelete.type === 'message') {
      deleteChatMessage(pendingDelete.messageId);
    } else if (pendingDelete.type === 'attachment') {
      removeAttachmentFromChat(pendingDelete.item);
    } else if (pendingDelete.type === 'conversation') {
      setMessages([]);
      setActiveOperation(null);
      setSearch('');
      setSearchOpen(false);
      setAttachments([]);
      setOptionsOpen(false);
      setPlusOpen(false);
    }

    setPendingDelete(null);
  }

  function startLongPress(action, event) {
    if (event.target.closest('button')) return;
    window.clearTimeout(longPressTimerRef.current);
    longPressTimerRef.current = window.setTimeout(action, 650);
  }

  function cancelLongPress() {
    window.clearTimeout(longPressTimerRef.current);
    longPressTimerRef.current = null;
  }

'''

marker = "  async function deleteAttachment(item) {"
index = source.find(marker)
if index == -1:
    raise RuntimeError('Não foi possível localizar a exclusão de anexos.')
source = source[:index] + helpers + source[index:]

source, count = re.subn(
    r"  async function deleteAttachment\(item\) \{.*?\n  \}\n\n  async function deleteConversation\(\) \{.*?\n  \}",
    '''  async function deleteAttachment(item) {
    removeAttachmentFromChat(item);
  }

  async function deleteConversation() {
    confirmDeleteConversation();
  }''',
    source,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError('Não foi possível tornar a exclusão da conversa independente da Biblioteca.')

article_old = '<article className={`chat-message ${message.role}${message.isError ? \' error\' : \'\'}`} key={message.id}>'
article_new = '''<article
                  className={`chat-message ${message.role}${message.isError ? ' error' : ''}`}
                  key={message.id}
                  onPointerDown={(event) => startLongPress(() => confirmDeleteMessage(message.id), event)}
                  onPointerUp={cancelLongPress}
                  onPointerCancel={cancelLongPress}
                  onPointerLeave={cancelLongPress}
                  onContextMenu={(event) => { event.preventDefault(); confirmDeleteMessage(message.id); }}
                >'''
if article_old not in source:
    raise RuntimeError('Não foi possível ativar a exclusão unitária nas mensagens.')
source = source.replace(article_old, article_new, 1)

image_old = '<figure className="chat-image-native" key={item.id}>'
image_new = '''<figure
                          className="chat-image-native"
                          key={item.id}
                          onPointerDown={(event) => { event.stopPropagation(); startLongPress(() => confirmDeleteAttachment(item), event); }}
                          onPointerUp={(event) => { event.stopPropagation(); cancelLongPress(); }}
                          onPointerCancel={cancelLongPress}
                          onPointerLeave={cancelLongPress}
                          onContextMenu={(event) => { event.preventDefault(); event.stopPropagation(); confirmDeleteAttachment(item); }}
                        >'''
if image_old not in source:
    raise RuntimeError('Não foi possível ativar a exclusão unitária nas imagens.')
source = source.replace(image_old, image_new, 1)

file_old = '<div className="chat-native-file" key={item.id}>'
file_new = '''<div
                          className="chat-native-file"
                          key={item.id}
                          onPointerDown={(event) => { event.stopPropagation(); startLongPress(() => confirmDeleteAttachment(item), event); }}
                          onPointerUp={(event) => { event.stopPropagation(); cancelLongPress(); }}
                          onPointerCancel={cancelLongPress}
                          onPointerLeave={cancelLongPress}
                          onContextMenu={(event) => { event.preventDefault(); event.stopPropagation(); confirmDeleteAttachment(item); }}
                        >'''
if file_old not in source:
    raise RuntimeError('Não foi possível ativar a exclusão unitária nos arquivos.')
source = source.replace(file_old, file_new, 1)

modal_marker = "      {sidebarOpen ? <button className=\"sidebar-backdrop\""
modal_index = source.find(modal_marker)
if modal_index == -1:
    raise RuntimeError('Não foi possível inserir a confirmação de exclusão.')
modal = '''      {pendingDelete ? (
        <div className="chat-delete-modal-backdrop" role="dialog" aria-modal="true" aria-label="Confirmar exclusão">
          <div className="chat-delete-modal">
            <button type="button" className="cancel" onClick={() => setPendingDelete(null)}>Cancelar</button>
            <button type="button" className="delete" onClick={executePendingDelete}>Apagar</button>
          </div>
        </div>
      ) : null}

'''
source = source[:modal_index] + modal + source[modal_index:]

path.write_text(source, encoding='utf-8')
