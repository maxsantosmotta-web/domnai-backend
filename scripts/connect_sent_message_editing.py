from pathlib import Path

DASHBOARD = Path('/frontend/src/Dashboard.jsx')
STYLES = Path('/frontend/src/dashboard-adjustments.css')

source = DASHBOARD.read_text(encoding='utf-8')

# References and state used only by the contextual action sheet.
if 'const composerInputRef = useRef(null);' not in source:
    anchor = '  const fileInputRef = useRef(null);\n'
    if anchor not in source:
        raise RuntimeError('Referência do campo de arquivos não localizada no Dashboard.')
    source = source.replace(anchor, anchor + '  const composerInputRef = useRef(null);\n', 1)

if 'const [messageActionTarget, setMessageActionTarget]' not in source:
    anchor = '  const [attachments, setAttachments] = useState([]);\n'
    if anchor not in source:
        raise RuntimeError('Estado de anexos não localizado no Dashboard final.')
    source = source.replace(
        anchor,
        anchor + '  const [messageActionTarget, setMessageActionTarget] = useState(null);\n',
        1,
    )

# The old deletion patch ignored the selectable text and opened a browser confirm.
# Long press now opens one contextual menu for the complete message.
source = source.replace(
    "    if (event.target.closest('button, .message-text-selectable')) return;",
    "    if (event.target.closest('button')) return;",
    1,
)

old_press = 'onPointerDown={(event) => startLongPress(() => confirmDeleteMessage(message.id), event)}'
new_press = 'onPointerDown={(event) => startLongPress(() => openMessageActions(message), event)}'
if old_press not in source and new_press not in source:
    raise RuntimeError('Ação de pressão longa da mensagem não localizada.')
source = source.replace(old_press, new_press, 1)

old_context = '''onContextMenu={(event) => {
                    if (!event.target.closest('.message-text-selectable')) event.preventDefault();
                  }}'''
new_context = '''onContextMenu={(event) => {
                    event.preventDefault();
                    openMessageActions(message);
                  }}'''
if old_context in source:
    source = source.replace(old_context, new_context, 1)

# Give the selectable text a stable DOM id for the explicit "Selecionar texto" action.
selectable_old = '''<span className="message-text-selectable" style={{ WebkitTouchCallout: 'default', userSelect: 'text' }}>{message.text}</span>'''
selectable_new = '''<span
                        id={`message-text-${message.id}`}
                        className="message-text-selectable"
                        style={{ WebkitTouchCallout: 'default', userSelect: 'text' }}
                      >
                        {message.text}
                      </span>'''
if 'id={`message-text-${message.id}`}' not in source:
    if selectable_old not in source:
        raise RuntimeError('Texto selecionável final da mensagem não localizado.')
    source = source.replace(selectable_old, selectable_new, 1)

if 'function openMessageActions(message)' not in source:
    marker = '  async function sendMessage(event) {'
    if marker not in source:
        raise RuntimeError('Função de envio não localizada no Dashboard final.')
    helpers = '''  function openMessageActions(message) {
    if (!message || message.processing || responding) return;
    setMessageActionTarget(message);
  }

  function closeMessageActions() {
    setMessageActionTarget(null);
  }

  async function copyMessageAction() {
    const text = String(messageActionTarget?.text || '');
    if (!text) return;
    await navigator.clipboard.writeText(text);
    closeMessageActions();
  }

  function selectMessageTextAction() {
    const messageId = messageActionTarget?.id;
    closeMessageActions();
    window.requestAnimationFrame(() => {
      const node = document.getElementById(`message-text-${messageId}`);
      if (!node) return;
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(node);
      selection.removeAllRanges();
      selection.addRange(range);
    });
  }

  function editSentMessage(messageId) {
    if (responding) return;
    const messageIndex = messages.findIndex((message) => message.id === messageId);
    if (messageIndex < 0) return;
    const message = messages[messageIndex];
    if (message.role !== 'user' || message.processing) return;

    setDraft(String(message.text || ''));
    setAttachments([...(message.attachments || [])]);
    setMessages(messages.slice(0, messageIndex));
    closeMessageActions();
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

  function deleteMessageAction() {
    const messageId = messageActionTarget?.id;
    closeMessageActions();
    if (messageId != null) confirmDeleteMessage(messageId);
  }

'''
    source = source.replace(marker, helpers + marker, 1)

if 'ref={composerInputRef}' not in source:
    textarea = '<textarea value={draft}'
    if textarea not in source:
        raise RuntimeError('Campo de mensagem não localizado no Dashboard final.')
    source = source.replace(textarea, '<textarea ref={composerInputRef} value={draft}', 1)

# Insert the action sheet immediately before the composer. It does not alter message layout.
if 'className="message-action-sheet"' not in source:
    marker = '            <form className="chat-composer'
    index = source.find(marker)
    if index < 0:
        raise RuntimeError('Compositor final não localizado para inserir o menu contextual.')
    sheet = '''            {messageActionTarget ? (
              <>
                <button
                  type="button"
                  className="message-action-backdrop"
                  aria-label="Fechar ações da mensagem"
                  onClick={closeMessageActions}
                />
                <aside className="message-action-sheet" role="menu" aria-label="Ações da mensagem">
                  <button type="button" role="menuitem" onClick={copyMessageAction}>Copiar</button>
                  <button type="button" role="menuitem" onClick={selectMessageTextAction}>Selecionar texto</button>
                  {messageActionTarget.role === 'user' ? (
                    <button type="button" role="menuitem" onClick={() => editSentMessage(messageActionTarget.id)}>Editar mensagem</button>
                  ) : null}
                  <button type="button" role="menuitem" className="danger" onClick={deleteMessageAction}>Apagar mensagem</button>
                </aside>
              </>
            ) : null}
'''
    source = source[:index] + sheet + source[index:]

required = (
    'const [messageActionTarget, setMessageActionTarget]',
    'function openMessageActions(message)',
    'function copyMessageAction()',
    'function selectMessageTextAction()',
    'function editSentMessage(messageId)',
    'function deleteMessageAction()',
    'startLongPress(() => openMessageActions(message), event)',
    'className="message-action-sheet"',
    'Editar mensagem',
    'ref={composerInputRef}',
    'id={`message-text-${message.id}`}',
)
for marker in required:
    if marker not in source:
        raise RuntimeError(f'Menu contextual de mensagem incompleto: {marker}')

# Guard the exact corruption previously rendered as visible text.
for forbidden in (
    'startLongPress(() => confirmDeleteMessage(message.id), event)} onPointerUp=',
    'onPointerUp=onPointerCancel=',
    'onPointerMove=onContextMenu=',
    'className="edit-sent-message-button"',
):
    if forbidden in source:
        raise RuntimeError(f'Markup antigo/corrompido permaneceu no chat: {forbidden}')

DASHBOARD.write_text(source, encoding='utf-8')

styles = STYLES.read_text(encoding='utf-8')
css = '''

/* sent-message-actions-final */
.message-action-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  border: 0;
  background: rgba(0, 0, 0, 0.48);
}

.message-action-sheet {
  position: fixed;
  left: 50%;
  bottom: max(22px, env(safe-area-inset-bottom));
  z-index: 81;
  width: min(420px, calc(100vw - 28px));
  transform: translateX(-50%);
  display: grid;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 22px;
  background: rgba(24, 24, 27, 0.98);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.48);
  backdrop-filter: blur(18px);
}

.message-action-sheet button {
  min-height: 54px;
  border: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: 600;
  text-align: left;
  padding: 0 22px;
}

.message-action-sheet button:last-child {
  border-bottom: 0;
}

.message-action-sheet button:active {
  background: rgba(255, 255, 255, 0.08);
}

.message-action-sheet button.danger {
  color: #ff8585;
}
'''
for marker in ('/* sent-message-editing-final */', '/* sent-message-actions-final */'):
    start = styles.find(marker)
    if start >= 0:
        styles = styles[:start].rstrip()
styles = styles.rstrip() + css + '\n'
STYLES.write_text(styles, encoding='utf-8')

print('Pressão longa conectada ao menu contextual: copiar, selecionar texto, editar mensagem enviada e apagar, sem botão permanente.')
