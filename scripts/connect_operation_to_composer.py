from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

if "const operationComposerRef = useRef(null);" not in source:
    source = source.replace(
        "  const fileInputRef = useRef(null);",
        "  const fileInputRef = useRef(null);\n  const operationComposerRef = useRef(null);",
        1,
    )

replacement = '''  function selectOperation(item) {
    if (responding) return;

    const lastMessage = messages[messages.length - 1];
    const alreadyCurrent = activeOperation === item.id && lastMessage?.role === 'operation';

    setActiveOperation(item.id);
    setSection('chat');
    setDraft(item.name);
    setAttachments([]);
    setPlusOpen(false);
    setSidebarOpen(false);

    if (!alreadyCurrent) {
      setMessages((current) => [...current, {
        id: `operation-${item.id}-${Date.now()}`,
        role: 'operation',
        text: '',
        operationId: item.id,
        attachments: [],
      }]);
    }

    window.setTimeout(() => {
      const composer = operationComposerRef.current;
      if (!composer) return;
      composer.scrollIntoView({ behavior: 'smooth', block: 'center' });
      window.setTimeout(() => {
        composer.querySelector('textarea')?.focus({ preventScroll: true });
      }, 450);
    }, 80);
  }
'''

source, count = re.subn(
    r"  (?:async )?function selectOperation\(item\) \{.*?\n  \}",
    replacement.rstrip(),
    source,
    count=1,
    flags=re.S,
)

if count != 1:
    raise RuntimeError('Não foi possível ajustar o fluxo de seleção da operação.')

form_old = '<form className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
form_new = '<form ref={operationComposerRef} className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
if form_old not in source:
    raise RuntimeError('Não foi possível conectar a rolagem à caixa de envio.')
source = source.replace(form_old, form_new, 1)

path.write_text(source, encoding='utf-8')
