from pathlib import Path
import re

DASHBOARD = Path('/frontend/src/Dashboard.jsx')
STYLES = Path('/frontend/src/dashboard-adjustments.css')

source = DASHBOARD.read_text(encoding='utf-8')

if 'const composerInputRef = useRef(null);' not in source:
    anchor = '  const fileInputRef = useRef(null);\n'
    if anchor not in source:
        raise RuntimeError('Referência do campo de arquivos não localizada no Dashboard.')
    source = source.replace(anchor, anchor + '  const composerInputRef = useRef(null);\n', 1)

if 'const [editingActionMessageId, setEditingActionMessageId]' not in source:
    anchor = '  const [responding, setResponding] = useState(false);\n'
    if anchor not in source:
        raise RuntimeError('Estado responding não localizado no Dashboard final.')
    source = source.replace(
        anchor,
        anchor + '  const [editingActionMessageId, setEditingActionMessageId] = useState(null);\n',
        1,
    )

if 'function toggleEditingAction(message)' not in source:
    marker = '  async function sendMessage(event) {'
    toggle = '''  function toggleEditingAction(message) {
    if (message.role !== 'user' || message.processing || responding) return;
    setEditingActionMessageId((current) => current === message.id ? null : message.id);
  }

'''
    if marker not in source:
        raise RuntimeError('Função de envio não localizada no Dashboard final.')
    source = source.replace(marker, toggle + marker, 1)

if 'function editSentMessage(messageId)' not in source:
    handler = '''  function editSentMessage(messageId) {
    if (responding) return;

    const messageIndex = messages.findIndex((message) => message.id === messageId);
    if (messageIndex < 0) return;

    const message = messages[messageIndex];
    if (message.role !== 'user' || message.processing) return;

    setDraft(String(message.text || ''));
    setAttachments([...(message.attachments || [])]);
    setMessages(messages.slice(0, messageIndex));
    setEditingActionMessageId(null);
    setSearch('');
    setSearchOpen(false);
    setOptionsOpen(false);
    setPlusOpen(false);

    window.requestAnimationFrame(() => {
      composerInputRef.current?.focus();
      const length = composerInputRef.current?.value?.length || 0;
      composerInputRef.current?.setSelectionRange?.(length, length);
    });
  }

'''
    marker = '  async function sendMessage(event) {'
    source = source.replace(marker, handler + marker, 1)

# Rebuild the final message-card opening after every previous frontend patch.
article_pattern = re.compile(r'<article\b.*?\bkey=\{message\.id\}.*?>', re.S)
article_replacement = '''<article
                  className={`chat-message ${message.role}${message.isError ? ' error' : ''}`}
                  key={message.id}
                  style={{ WebkitTouchCallout: 'default', userSelect: 'none' }}
                  onClick={(event) => {
                    if (!event.target.closest('button, a')) toggleEditingAction(message);
                  }}
                  onPointerDown={(event) => startLongPress(() => confirmDeleteMessage(message.id), event)}
                  onPointerUp={finishLongPress}
                  onPointerCancel={cancelLongPress}
                  onPointerMove={moveLongPress}
                  onContextMenu={(event) => {
                    if (!event.target.closest('.message-text-selectable')) event.preventDefault();
                  }}
                >'''
source, article_count = article_pattern.subn(article_replacement, source, count=1)
if article_count != 1:
    raise RuntimeError('Cartão final de mensagem não localizado para reconstrução segura.')

if 'className="edit-sent-message-button"' not in source:
    author = '<span className="message-author">{message.role === \'assistant\' ? \'DomnAI\' : \'Você\'}</span>'
    replacement = '''<div className={`message-heading${editingActionMessageId === message.id ? ' editing-action-open' : ''}`}>
                    <span className="message-author">{message.role === 'assistant' ? 'DomnAI' : 'Você'}</span>
                    {message.role === 'user' && !message.processing ? (
                      <button
                        type="button"
                        className="edit-sent-message-button"
                        onClick={(event) => {
                          event.stopPropagation();
                          editSentMessage(message.id);
                        }}
                        disabled={responding}
                        aria-label="Editar mensagem enviada"
                        title="Editar mensagem"
                      >
                        Editar
                      </button>
                    ) : null}
                  </div>'''
    if author not in source:
        raise RuntimeError('Cabeçalho das mensagens não localizado no Dashboard final.')
    source = source.replace(author, replacement, 1)

if 'ref={composerInputRef}' not in source:
    source, count = re.subn(
        r'<textarea\s+value=\{draft\}',
        '<textarea ref={composerInputRef} value={draft}',
        source,
        count=1,
    )
    if count != 1:
        raise RuntimeError('Campo de mensagem não localizado no Dashboard final.')

for marker in (
    'const composerInputRef = useRef(null);',
    'editingActionMessageId',
    'function toggleEditingAction(message)',
    'function editSentMessage(messageId)',
    'className="edit-sent-message-button"',
    'editing-action-open',
    'event.stopPropagation();',
    'ref={composerInputRef}',
    'setMessages(messages.slice(0, messageIndex));',
    'onPointerDown={(event) => startLongPress(() => confirmDeleteMessage(message.id), event)}',
):
    if marker not in source:
        raise RuntimeError(f'Edição de mensagem incompleta: {marker}')

DASHBOARD.write_text(source, encoding='utf-8')

styles = STYLES.read_text(encoding='utf-8')
css = '''

/* sent-message-editing-final */
.message-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.edit-sent-message-button {
  display: none !important;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.76rem;
  line-height: 1;
  padding: 5px 7px;
  cursor: pointer;
  border-radius: 7px;
}

@media (hover: hover) and (pointer: fine) {
  .chat-message.user:hover .edit-sent-message-button {
    display: inline-flex !important;
  }
}

.message-heading.editing-action-open .edit-sent-message-button {
  display: inline-flex !important;
}

.edit-sent-message-button:hover,
.edit-sent-message-button:focus-visible {
  background: rgba(127, 127, 127, 0.14);
  outline: none;
}

.edit-sent-message-button:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}
'''
start = styles.find('/* sent-message-editing-final */')
if start >= 0:
    styles = styles[:start].rstrip()
styles = styles.rstrip() + css + '\n'
STYLES.write_text(styles, encoding='utf-8')

print('Cartão final reconstruído: exclusão por pressão longa preservada e edição contextual ligada à mensagem inteira sem sobreposição.')
