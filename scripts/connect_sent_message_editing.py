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
    marker = '  function editSentMessage(messageId) {'
    if marker not in source:
        marker = '  async function sendMessage(event) {'
    toggle = '''  function toggleEditingAction(message) {
    if (message.role !== 'user' || message.processing || responding) return;
    setEditingActionMessageId((current) => current === message.id ? null : message.id);
  }

'''
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
    if marker not in source:
        raise RuntimeError('Função de envio não localizada no Dashboard final.')
    source = source.replace(marker, handler + marker, 1)

if 'className="edit-sent-message-button"' not in source:
    author = '<span className="message-author">{message.role === \'assistant\' ? \'DomnAI\' : \'Você\'}</span>'
    replacement = '''<div
                    className={`message-heading${editingActionMessageId === message.id ? ' editing-action-open' : ''}`}
                    onClick={() => toggleEditingAction(message)}
                  >
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

plain_text = '{message.text ? <p>{message.text}</p> : null}'
interactive_text = '''{message.text ? (
                    <p
                      className={message.role === 'user' ? 'editable-message-body' : undefined}
                      onClick={() => toggleEditingAction(message)}
                    >
                      {message.text}
                    </p>
                  ) : null}'''
if 'editable-message-body' not in source:
    if plain_text not in source:
        raise RuntimeError('Corpo textual da mensagem não localizado no Dashboard final.')
    source = source.replace(plain_text, interactive_text, 1)

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
    'editable-message-body',
    'editing-action-open',
    'event.stopPropagation();',
    'ref={composerInputRef}',
    'setMessages(messages.slice(0, messageIndex));',
):
    if marker not in source:
        raise RuntimeError(f'Edição de mensagem incompleta: {marker}')

DASHBOARD.write_text(source, encoding='utf-8')

styles = STYLES.read_text(encoding='utf-8')
css = '''

/* sent-message-editing-final */
.chat-message.user {
  position: relative;
}

.message-heading {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editable-message-body {
  cursor: pointer;
}

.edit-sent-message-button {
  display: none !important;
  position: absolute;
  right: 8px;
  bottom: -28px;
  z-index: 4;
  border: 1px solid rgba(127, 127, 127, 0.24);
  background: rgba(20, 20, 20, 0.96);
  color: inherit;
  font: inherit;
  font-size: 0.76rem;
  line-height: 1;
  padding: 7px 10px;
  cursor: pointer;
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
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
  background: rgba(38, 38, 38, 0.98);
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

print('Edição móvel conectada ao corpo inteiro da mensagem, sem sobrepor o conteúdo da caixa.')
