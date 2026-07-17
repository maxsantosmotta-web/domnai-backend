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

if "const browserReloadPendingRef = useRef(true);" not in source:
    marker = "  const chatScrollRef = useRef(null);"
    source = source.replace(
        marker,
        marker + "\n  const browserReloadPendingRef = useRef(true);",
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


def operation_marker(current_source: str) -> str:
    async_marker = "  async function selectOperation(item) {"
    sync_marker = "  function selectOperation(item) {"
    if async_marker in current_source:
        return async_marker
    if sync_marker in current_source:
        return sync_marker
    raise RuntimeError('Não foi possível localizar o ponto seguro do chat.')


scroll_tracking_effect = r'''
  useEffect(() => {
    if (section !== 'chat') return undefined;

    const chatArea = chatScrollRef.current;
    if (!chatArea) return undefined;

    const rememberBottomState = () => {
      const distanceFromBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight;
      window.sessionStorage.setItem('domnai-chat-was-at-bottom', distanceFromBottom <= 24 ? '1' : '0');
    };

    rememberBottomState();
    chatArea.addEventListener('scroll', rememberBottomState, { passive: true });
    window.addEventListener('pagehide', rememberBottomState);

    return () => {
      chatArea.removeEventListener('scroll', rememberBottomState);
      window.removeEventListener('pagehide', rememberBottomState);
    };
  }, [section, conversationReady]);

'''

if "domnai-chat-was-at-bottom" not in source:
    marker = operation_marker(source)
    source = source.replace(marker, scroll_tracking_effect + marker, 1)

single_effect = r'''
  useLayoutEffect(() => {
    if (section !== 'chat' || !conversationReady || messages.length === 0) return undefined;

    const chatArea = chatScrollRef.current;
    if (!chatArea) return undefined;

    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }

    const distanceFromBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight;
    const isBrowserReload = browserReloadPendingRef.current;

    if (isBrowserReload) {
      browserReloadPendingRef.current = false;
      const wasAtBottom = window.sessionStorage.getItem('domnai-chat-was-at-bottom') === '1';

      if (wasAtBottom) {
        chatArea.scrollTop = chatArea.scrollHeight;
        return undefined;
      }
    }

    if (distanceFromBottom <= 2) return undefined;

    const frame = window.requestAnimationFrame(() => {
      chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'smooth' });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [section, conversationReady, messages.length, chatRefreshTick]);

'''

existing_effect_pattern = re.compile(
    r"\n  useLayoutEffect\(\(\) => \{\n"
    r"    if \(section !== 'chat' \|\| !conversationReady\).*?"
    r"  \}, \[section, conversationReady, messages\.length, chatRefreshTick\]\);\n\n",
    re.S,
)
source, effect_count = existing_effect_pattern.subn("\n" + single_effect.lstrip("\n"), source, count=1)

if effect_count == 0 and "[section, conversationReady, messages.length, chatRefreshTick]" not in source:
    marker = operation_marker(source)
    source = source.replace(marker, single_effect + marker, 1)
elif effect_count == 0:
    raise RuntimeError('Não foi possível substituir com segurança o controlador atual de rolagem.')

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

# Corrige apenas contenção e quebra de textos longos nas mensagens.
css_path = Path('/frontend/src/dashboard.css')
css = css_path.read_text(encoding='utf-8')
message_fix = """

/* Mantém textos, links e tabelas textuais dentro da caixa da mensagem. */
.chat-message,
.chat-message p {
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.chat-message p,
.chat-message pre,
.chat-message code {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.chat-message pre,
.chat-message code {
  max-width: 100%;
  white-space: pre-wrap;
}
"""
if 'Mantém textos, links e tabelas textuais dentro da caixa da mensagem.' not in css:
    css = css.rstrip() + message_fix + '\n'
css_path.write_text(css, encoding='utf-8')