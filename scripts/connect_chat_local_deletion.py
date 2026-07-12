from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

source = source.replace(
    "import './dashboard-delete-modal.css';\n",
    "",
    1,
)

source = source.replace(
    "  const fileInputRef = useRef(null);",
    "  const fileInputRef = useRef(null);\n  const longPressTimerRef = useRef(null);\n  const longPressActionRef = useRef(null);\n  const deletePromptLockedRef = useRef(false);",
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

  function runSingleDeletePrompt(text, onConfirm) {
    if (deletePromptLockedRef.current) return;
    deletePromptLockedRef.current = true;
    const confirmed = window.confirm(text);
    if (confirmed) onConfirm();
    window.setTimeout(() => {
      deletePromptLockedRef.current = false;
    }, 500);
  }

  function confirmDeleteMessage(messageId) {
    runSingleDeletePrompt('Apagar esta mensagem?', () => deleteChatMessage(messageId));
  }

  function confirmDeleteAttachment(item) {
    runSingleDeletePrompt('Apagar este item da conversa?', () => removeAttachmentFromChat(item));
  }

  function startLongPress(action, event) {
    if (event.target.closest('button')) return;
    window.clearTimeout(longPressTimerRef.current);
    longPressActionRef.current = null;
    longPressTimerRef.current = window.setTimeout(() => {
      longPressTimerRef.current = null;
      longPressActionRef.current = action;
    }, 650);
  }

  function finishLongPress() {
    window.clearTimeout(longPressTimerRef.current);
    longPressTimerRef.current = null;
    const action = longPressActionRef.current;
    longPressActionRef.current = null;
    if (action) window.setTimeout(action, 0);
  }

  function cancelLongPress() {
    window.clearTimeout(longPressTimerRef.current);
    longPressTimerRef.current = null;
    longPressActionRef.current = null;
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
    runSingleDeletePrompt('Apagar a conversa?', () => {
      setMessages([]);
      setActiveOperation(null);
      setSearch('');
      setSearchOpen(false);
      setAttachments([]);
      setOptionsOpen(false);
      setPlusOpen(false);
    });
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
                  style={{ WebkitTouchCallout: 'none', userSelect: 'none' }}
                  onPointerDown={(event) => startLongPress(() => confirmDeleteMessage(message.id), event)}
                  onPointerUp={finishLongPress}
                  onPointerCancel={cancelLongPress}
                  onPointerMove={cancelLongPress}
                  onPointerLeave={cancelLongPress}
                  onContextMenu={(event) => { event.preventDefault(); }}
                >'''
if article_old not in source:
    raise RuntimeError('Não foi possível ativar a exclusão unitária nas mensagens.')
source = source.replace(article_old, article_new, 1)

image_old = '<figure className="chat-image-native" key={item.id}>'
image_new = '''<figure
                          className="chat-image-native"
                          key={item.id}
                          style={{ WebkitTouchCallout: 'none', userSelect: 'none' }}
                          onPointerDown={(event) => { event.stopPropagation(); startLongPress(() => confirmDeleteAttachment(item), event); }}
                          onPointerUp={(event) => { event.stopPropagation(); finishLongPress(); }}
                          onPointerCancel={cancelLongPress}
                          onPointerMove={cancelLongPress}
                          onPointerLeave={cancelLongPress}
                          onContextMenu={(event) => { event.preventDefault(); event.stopPropagation(); }}
                        >'''
if image_old not in source:
    raise RuntimeError('Não foi possível ativar a exclusão unitária nas imagens.')
source = source.replace(image_old, image_new, 1)

file_old = '<div className="chat-native-file" key={item.id}>'
file_new = '''<div
                          className="chat-native-file"
                          key={item.id}
                          style={{ WebkitTouchCallout: 'none', userSelect: 'none' }}
                          onPointerDown={(event) => { event.stopPropagation(); startLongPress(() => confirmDeleteAttachment(item), event); }}
                          onPointerUp={(event) => { event.stopPropagation(); finishLongPress(); }}
                          onPointerCancel={cancelLongPress}
                          onPointerMove={cancelLongPress}
                          onPointerLeave={cancelLongPress}
                          onContextMenu={(event) => { event.preventDefault(); event.stopPropagation(); }}
                        >'''
if file_old not in source:
    raise RuntimeError('Não foi possível ativar a exclusão unitária nos arquivos.')
source = source.replace(file_old, file_new, 1)

path.write_text(source, encoding='utf-8')
