from pathlib import Path

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
    if marker not in source:
        raise RuntimeError('Função de envio não localizada no Dashboard final.')
    toggle = '''  function toggleEditingAction(message) {
    if (message.role !== 'user' || message.processing || responding) return;
    setEditingActionMessageId((current) => current === message.id ? null : message.id);
  }

'''
    source = source.replace(marker, toggle + marker, 1)

if 'function editSentMessage(messageId)' not in source:
    marker = '  async function sendMessage(event) {'
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
    source = source.replace(marker, handler + marker, 1)

# Do not alter the message-card opening. The deletion patch owns that markup.
# Attach the mobile interaction only to the already selectable message text.
selectable_old = '''<span className="message-text-selectable" style={{ WebkitTouchCallout: 'default', userSelect: 'text' }}>{message.text}</span>'''
selectable_new = '''<span
                        className="message-text-selectable"
                        style={{ WebkitTouchCallout: 'default', userSelect: 'text' }}
                        onClick={(event) => {
                          event.stopPropagation();
                          toggleEditingAction(message);
                        }}
                      >
                        {message.text}
                      </span>'''
if 'toggleEditingAction(message);' not in source.split('message-text-selectable', 1)[-1]:
    if selectable_old not in source:
        raise RuntimeError('Texto selecionável final da mensagem não localizado.')
    source = source.replace(selectable_old, selectable_new, 1)

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
    textarea = '<textarea value={draft}'
    if textarea not in source:
        raise RuntimeError('Campo de mensagem não localizado no Dashboard final.')
    source = source.replace(textarea, '<textarea ref={composerInputRef} value={draft}', 1)

for marker in (
    'const composerInputRef = useRef(null);',
    'editingActionMessageId',
    'function toggleEditingAction(message)',
    'function editSentMessage(messageId)',
    'className="edit-sent-message-button"',
    'editing-action-open',
    'ref={composerInputRef}',
    'setMessages(messages.slice(0, messageIndex));',
    'className="message-text-selectable"',
):
    if marker not in source:
        raise RuntimeError(f'Edição de mensagem incompleta: {marker}')

# Explicit guard against the corruption seen in production.
for forbidden in (
    'startLongPress(() => confirmDeleteMessage(message.id), event)} onPointerUp=',
    'onPointerUp=onPointerCancel=',
    'onPointerMove=onContextMenu=',
):
    if forbidden in source:
        raise RuntimeError(f'Markup do cartão de mensagem corrompido: {forbidden}')

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

print('Edição contextual isolada: cartão original preservado; toque no texto revela Editar sem interferir em copiar ou apagar.')
