from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

# Uma única implementação para as duas formas de atualização do chat.
source = source.replace(
    "import React, { useEffect, useMemo, useRef, useState } from 'react';",
    "import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';",
    1,
)

if "const chatScrollRef = useRef(null);" not in source:
    marker = "  const fileInputRef = useRef(null);"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar os refs do Dashboard.')
    source = source.replace(marker, marker + "\n  const chatScrollRef = useRef(null);", 1)

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
    if (!chatArea) return undefined;

    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }

    const distanceFromBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight;
    if (distanceFromBottom <= 2) return undefined;

    const frame = window.requestAnimationFrame(() => {
      chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'smooth' });
    });

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

path.write_text(source, encoding='utf-8')