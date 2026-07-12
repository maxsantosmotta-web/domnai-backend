from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

source = source.replace(
    "import React, { useEffect, useMemo, useRef, useState } from 'react';",
    "import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';",
    1,
)
source = source.replace(
    "import React, { useMemo, useRef, useState } from 'react';",
    "import React, { useLayoutEffect, useMemo, useRef, useState } from 'react';",
    1,
)

if "import './dashboard-chat-scroll.css';" not in source:
    source = source.replace(
        "import './dashboard-operation-blocks.css';",
        "import './dashboard-operation-blocks.css';\nimport './dashboard-chat-scroll.css';",
        1,
    )

if "const chatScrollRef = useRef(null);" not in source:
    source = source.replace(
        "  const fileInputRef = useRef(null);",
        "  const fileInputRef = useRef(null);\n  const operationComposerRef = useRef(null);\n  const chatScrollRef = useRef(null);\n  const [composerScrollRequest, setComposerScrollRequest] = useState(0);",
        1,
    )

scroll_effect = '''
  useLayoutEffect(() => {
    if (!composerScrollRequest || section !== 'chat') return;
    const chatArea = chatScrollRef.current;
    if (!chatArea) return;
    chatArea.scrollTop = chatArea.scrollHeight;
  }, [composerScrollRequest, section, messages.length]);

'''

if "useLayoutEffect(() =>" not in source:
    match = re.search(r"  (?:async )?function selectOperation\(item\) \{", source)
    if not match:
        raise RuntimeError('Não foi possível localizar a seleção de operação.')
    source = source[:match.start()] + scroll_effect + source[match.start():]

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

    setComposerScrollRequest((current) => current + 1);
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

refresh_replacement = '''  function refreshConversation() {
    setSection('chat');
    setSearch('');
    setSearchOpen(false);
    setOptionsOpen(false);
    setPlusOpen(false);
    setComposerScrollRequest((current) => current + 1);
  }'''

source, refresh_count = re.subn(
    r"  function refreshConversation\(\) \{.*?\n  \}",
    refresh_replacement,
    source,
    count=1,
    flags=re.S,
)
if refresh_count != 1:
    raise RuntimeError('Não foi possível ajustar o botão Atualizar conversa.')

chat_old = '<div className="chat-messages clean-chat-area">'
chat_new = '<div ref={chatScrollRef} className="chat-messages clean-chat-area">'
if chat_old not in source:
    raise RuntimeError('Não foi possível conectar a área rolável do chat.')
source = source.replace(chat_old, chat_new, 1)

form_old = '<form className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
form_new = '<form ref={operationComposerRef} className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
if form_old not in source:
    raise RuntimeError('Não foi possível conectar a caixa de envio.')
source = source.replace(form_old, form_new, 1)

path.write_text(source, encoding='utf-8')
