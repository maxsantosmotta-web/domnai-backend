from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

source = source.replace(
    "import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';",
    "import React, { useEffect, useMemo, useRef, useState } from 'react';",
    1,
)
source = source.replace(
    "import React, { useLayoutEffect, useMemo, useRef, useState } from 'react';",
    "import React, { useEffect, useMemo, useRef, useState } from 'react';",
    1,
)
source = source.replace("import './dashboard-chat-scroll.css';\n", "", 1)

if "const operationComposerRef = useRef(null);" not in source:
    source = source.replace(
        "  const fileInputRef = useRef(null);",
        "  const fileInputRef = useRef(null);\n  const operationComposerRef = useRef(null);\n  const initialConversationScrollDoneRef = useRef(false);\n  const [composerScrollRequest, setComposerScrollRequest] = useState(0);",
        1,
    )

scroll_effect = '''
  useEffect(() => {
    if (!composerScrollRequest || section !== 'chat') return undefined;

    const scrollToComposer = () => {
      const composer = operationComposerRef.current;
      if (!composer) return;
      composer.scrollIntoView({ behavior: 'smooth', block: 'end', inline: 'nearest' });
      const page = document.scrollingElement || document.documentElement;
      page.scrollTo({ top: page.scrollHeight, behavior: 'smooth' });
    };

    const frame = window.requestAnimationFrame(scrollToComposer);
    const timer = window.setTimeout(scrollToComposer, 120);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [composerScrollRequest, section, messages.length]);

  useEffect(() => {
    if (!conversationReady || section !== 'chat' || initialConversationScrollDoneRef.current) return undefined;
    initialConversationScrollDoneRef.current = true;
    const timer = window.setTimeout(() => {
      setComposerScrollRequest((current) => current + 1);
    }, 180);
    return () => window.clearTimeout(timer);
  }, [conversationReady, section]);

  useEffect(() => {
    const returnToChat = () => {
      window.setTimeout(() => {
        setComposerScrollRequest((current) => current + 1);
      }, 220);
    };
    window.addEventListener('domnai-return-to-chat', returnToChat);
    return () => window.removeEventListener('domnai-return-to-chat', returnToChat);
  }, []);

'''

if "window.addEventListener('domnai-return-to-chat'" not in source:
    match = re.search(r"  (?:async )?function selectOperation\(item\) \{", source)
    if not match:
        raise RuntimeError('Não foi possível localizar a seleção de operação.')
    source = source[:match.start()] + scroll_effect + source[match.start():]

replacement = '''  function selectOperation(item) {
    if (responding) return;

    setActiveOperation(item.id);
    setSection('chat');
    setAttachments([]);
    setPlusOpen(false);
    setSidebarOpen(false);

    window.setTimeout(() => {
      setDraft(item.name);
      setComposerScrollRequest((current) => current + 1);
    }, 240);
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

attach_old = """      setSection('chat');
      setPlusOpen(false);"""
attach_new = """      setSection('chat');
      setPlusOpen(false);
      window.setTimeout(() => {
        setComposerScrollRequest((current) => current + 1);
      }, 180);"""
if attach_old not in source:
    raise RuntimeError('Não foi possível ajustar o retorno da Biblioteca ao chat.')
source = source.replace(attach_old, attach_new, 1)

source = source.replace(
    '<div ref={chatScrollRef} className="chat-messages clean-chat-area">',
    '<div className="chat-messages clean-chat-area">',
    1,
)

form_old = '<form className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
form_new = '<form ref={operationComposerRef} className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
if form_old not in source:
    raise RuntimeError('Não foi possível conectar a caixa de envio.')
source = source.replace(form_old, form_new, 1)

path.write_text(source, encoding='utf-8')
