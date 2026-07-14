from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

# Garante useLayoutEffect para posicionar antes da pintura visível.
source = source.replace(
    "import React, { useEffect, useMemo, useRef, useState } from 'react';",
    "import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';",
    1,
)

# Substitui qualquer helper antigo que mandava ao topo ou usava rolagem suave.
helper_pattern = re.compile(
    r"  function scrollConversationFromTopToBottom\(\) \{.*?\n  \}\n",
    re.S,
)
helper = '''  function scrollConversationFromTopToBottom() {
    const chatArea = chatScrollRef.current;
    if (!chatArea) return;

    const pinToBottom = () => {
      chatArea.scrollTop = chatArea.scrollHeight;
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'auto' });
    };

    pinToBottom();
    window.requestAnimationFrame(pinToBottom);
    window.setTimeout(pinToBottom, 80);
    window.setTimeout(pinToBottom, 220);
  }
'''
source, helper_count = helper_pattern.subn(helper, source, count=1)
if helper_count != 1:
    raise RuntimeError('Não foi possível localizar o helper de rolagem do chat.')

# Regra única para recarregamento do navegador: nunca vai ao topo e nunca anima.
initial_pattern = re.compile(
    r"  use(?:Effect|LayoutEffect)\(\(\) => \{\n"
    r"    if \(\n"
    r"      section !== 'chat'.*?"
    r"  \}, \[section, conversationReady, messages\.length\]\);\n\n",
    re.S,
)
initial_effect = '''  useLayoutEffect(() => {
    if (
      section !== 'chat'
      || !conversationReady
      || messages.length === 0
      || initialBrowserScrollDoneRef.current
    ) return undefined;

    const chatArea = chatScrollRef.current;
    if (!chatArea) return undefined;

    initialBrowserScrollDoneRef.current = true;
    const previousRestoration = window.history.scrollRestoration;
    window.history.scrollRestoration = 'manual';

    let cancelled = false;
    const pinToBottom = () => {
      if (cancelled) return;
      chatArea.scrollTop = chatArea.scrollHeight;
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'auto' });
    };

    pinToBottom();
    const frameOne = window.requestAnimationFrame(pinToBottom);
    const frameTwo = window.requestAnimationFrame(() => window.requestAnimationFrame(pinToBottom));
    const timers = [60, 160, 320, 640].map((delay) => window.setTimeout(pinToBottom, delay));

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(frameOne);
      window.cancelAnimationFrame(frameTwo);
      timers.forEach((timer) => window.clearTimeout(timer));
      window.history.scrollRestoration = previousRestoration;
    };
  }, [section, conversationReady, messages.length]);

'''
source, effect_count = initial_pattern.subn(initial_effect, source, count=1)
if effect_count != 1:
    raise RuntimeError('Não foi possível localizar o efeito inicial de rolagem do chat.')

path.write_text(source, encoding='utf-8')