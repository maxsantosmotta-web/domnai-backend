from pathlib import Path
import re

# Controlador único para atualização externa e interna do chat.
dashboard_path = Path('/frontend/src/Dashboard.jsx')
source = dashboard_path.read_text(encoding='utf-8')

source = source.replace(
    "import React, { useEffect, useMemo, useRef, useState } from 'react';",
    "import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';",
    1,
)

if "const chatScrollRef = useRef(null);" not in source:
    marker = "  const fileInputRef = useRef(null);"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar os refs do Dashboard.')
    source = source.replace(
        marker,
        marker + "\n  const chatScrollRef = useRef(null);\n  const chatBottomRef = useRef(null);",
        1,
    )
elif "const chatBottomRef = useRef(null);" not in source:
    source = source.replace(
        "  const chatScrollRef = useRef(null);",
        "  const chatScrollRef = useRef(null);\n  const chatBottomRef = useRef(null);",
        1,
    )

if "const [chatRefreshTick, setChatRefreshTick]" not in source:
    marker = "  const [uploading, setUploading] = useState(false);"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar os estados do chat.')
    source = source.replace(
        marker,
        marker + "\n  const [chatRefreshTick, setChatRefreshTick] = useState(0);",
        1,
    )

single_effect = r'''
  useLayoutEffect(() => {
    if (section !== 'chat' || !conversationReady) return undefined;

    const chatArea = chatScrollRef.current;
    const bottomAnchor = chatBottomRef.current;
    if (!chatArea || !bottomAnchor) return undefined;

    const pinToBottom = () => {
      bottomAnchor.scrollIntoView({ block: 'end', behavior: 'auto' });
      chatArea.scrollTop = chatArea.scrollHeight;
    };

    pinToBottom();
    const frame = window.requestAnimationFrame(pinToBottom);

    return () => window.cancelAnimationFrame(frame);
  }, [section, conversationReady, messages.length, chatRefreshTick]);

'''

if "[section, conversationReady, messages.length, chatRefreshTick]" not in source:
    marker = "  function selectOperation(item) {"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o ponto seguro do chat.')
    source = source.replace(marker, single_effect + marker, 1)

new_refresh = r'''  async function refreshConversation() {
    setSearch('');
    setSearchOpen(false);
    setAttachments([]);
    setOptionsOpen(false);
    setPlusOpen(false);

    try {
      const response = await authorizedFetch('/api/chat-state');
      if (!response.ok) throw new Error('Não foi possível atualizar a conversa.');
      const payload = await response.json();
      setMessages(Array.isArray(payload.messages) ? payload.messages : []);
      setActiveOperation(payload.activeOperation || null);
      setChatRefreshTick((current) => current + 1);
    } catch (error) {
      window.alert(error.message || 'Não foi possível atualizar a conversa.');
    }
  }'''

source, count = re.subn(
    r"  (?:async )?function refreshConversation\(\) \{.*?\n  \}",
    new_refresh,
    source,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError('Não foi possível substituir a atualização interna do chat.')

old_chat_area = '<div className="chat-messages clean-chat-area">'
new_chat_area = '<div ref={chatScrollRef} className="chat-messages clean-chat-area">'
if old_chat_area in source:
    source = source.replace(old_chat_area, new_chat_area, 1)
elif new_chat_area not in source:
    raise RuntimeError('Não foi possível localizar o container de mensagens.')

bottom_anchor = '              <div ref={chatBottomRef} className="chat-bottom-anchor" aria-hidden="true" />\n'
if 'className="chat-bottom-anchor"' not in source:
    marker = '            </div>\n            <form className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o final da conversa.')
    source = source.replace(marker, bottom_anchor + marker, 1)

dashboard_path.write_text(source, encoding='utf-8')

# Impede o navegador de restaurar uma posição antiga antes do React montar.
main_path = Path('/frontend/src/main.jsx')
main_source = main_path.read_text(encoding='utf-8')
restoration_guard = """if ('scrollRestoration' in window.history) {\n  window.history.scrollRestoration = 'manual';\n}\n\n"""
if "window.history.scrollRestoration = 'manual';" not in main_source:
    marker = "const rootElement = document.getElementById('root');\n"
    if marker not in main_source:
        raise RuntimeError('Não foi possível localizar a montagem principal da aplicação.')
    main_source = main_source.replace(marker, restoration_guard + marker, 1)
main_path.write_text(main_source, encoding='utf-8')

# O marcador final mantém o rodapé ancorado enquanto o conteúdo termina de dimensionar.
css_path = Path('/frontend/src/dashboard.css')
css = css_path.read_text(encoding='utf-8')
anchor_css = """
.clean-chat-area > * {
  overflow-anchor: none;
}

.clean-chat-area .chat-bottom-anchor {
  width: 100%;
  height: 1px;
  min-height: 1px;
  flex: 0 0 1px;
  overflow-anchor: auto;
  pointer-events: none;
}
"""
if '.chat-bottom-anchor' not in css:
    css = css.rstrip() + '\n\n' + anchor_css.lstrip()
css_path.write_text(css, encoding='utf-8')
