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
    author_pattern = re.compile(
        r'(?P<indent>\s*)<span className="message-author">\{message\.role === \'assistant\' \? \'DomnAI\' : \'Você\'\}</span>'
    )
    replacement = '''\g<indent><div className="message-heading">
\g<indent>  <span className="message-author">{message.role === 'assistant' ? 'DomnAI' : 'Você'}</span>
\g<indent>  {message.role === 'user' && !message.processing ? (
\g<indent>    <button
\g<indent>      type="button"
\g<indent>      className="edit-sent-message-button"
\g<indent>      onClick={() => editSentMessage(message.id)}
\g<indent>      disabled={responding}
\g<indent>      aria-label="Editar mensagem enviada"
\g<indent>      title="Editar mensagem"
\g<indent>    >
\g<indent>      Editar
\g<indent>    </button>
\g<indent>  ) : null}
\g<indent></div>'''
    source, count = author_pattern.subn(replacement, source, count=1)
    if count != 1:
        raise RuntimeError('Cabeçalho das mensagens não localizado no Dashboard final.')

if "tabIndex={message.role === 'user' ? 0 : undefined}" not in source:
    source, count = re.subn(
        r'(<article className=\{`chat-message \$\{message\.role\}\$\{message\.isError \? \' error\' : \'\'\}`\} key=\{message\.id\})>',
        r"\1 tabIndex={message.role === 'user' ? 0 : undefined}>",
        source,
        count=1,
    )
    if count != 1:
        source, count = re.subn(
            r'(<article className=\{`chat-message \$\{message\.role\}`\} key=\{message\.id\})>',
            r"\1 tabIndex={message.role === 'user' ? 0 : undefined}>",
            source,
            count=1,
        )
    if count != 1:
        raise RuntimeError('Cartão de mensagem não localizado para interação contextual.')

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
    'function editSentMessage(messageId)',
    'className="edit-sent-message-button"',
    'ref={composerInputRef}',
    "tabIndex={message.role === 'user' ? 0 : undefined}",
    'setMessages(messages.slice(0, messageIndex));',
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
  font-size: 0.78rem;
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 6px;
}

@media (hover: hover) and (pointer: fine) {
  .chat-message.user:hover .edit-sent-message-button,
  .chat-message.user:focus-within .edit-sent-message-button {
    display: inline-flex !important;
  }
}

@media (hover: none), (pointer: coarse) {
  .chat-message.user:focus .edit-sent-message-button,
  .chat-message.user:focus-within .edit-sent-message-button {
    display: inline-flex !important;
  }
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

.chat-message.user:focus {
  outline: none;
}
'''
if '/* sent-message-editing-final */' not in styles:
    styles = styles.rstrip() + css + '\n'
STYLES.write_text(styles, encoding='utf-8')

print('Edição contextual aplicada com override final seguro: invisível por padrão e visível apenas após interação.')
