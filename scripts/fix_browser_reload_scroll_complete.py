from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

# useLayoutEffect posiciona o histórico antes da pintura da tela,
# evitando qualquer deslocamento visual no recarregamento do navegador.
source = source.replace(
    "import React, { useEffect, useMemo, useRef, useState } from 'react';",
    "import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';",
    1,
)

ref_line = "  const initialBrowserScrollDoneRef = useRef(false);"
if ref_line not in source:
    marker = "  const chatScrollRef = useRef(null);"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o ref do container do chat.')
    source = source.replace(marker, marker + "\n" + ref_line, 1)

new_effect = r'''  useLayoutEffect(() => {
    if (
      section !== 'chat'
      || !conversationReady
      || messages.length === 0
      || initialBrowserScrollDoneRef.current
    ) return undefined;

    const chatArea = chatScrollRef.current;
    if (!chatArea) return undefined;

    initialBrowserScrollDoneRef.current = true;
    chatArea.style.visibility = 'hidden';
    chatArea.scrollTop = chatArea.scrollHeight;

    let cancelled = false;
    let lastHeight = chatArea.scrollHeight;
    let stableChecks = 0;
    let checks = 0;
    let timer = null;

    const keepPinnedUntilStable = () => {
      if (cancelled) return;

      chatArea.scrollTop = chatArea.scrollHeight;
      const currentHeight = chatArea.scrollHeight;
      stableChecks = currentHeight === lastHeight ? stableChecks + 1 : 0;
      lastHeight = currentHeight;
      checks += 1;

      if (stableChecks >= 3 || checks >= 20) {
        chatArea.scrollTop = chatArea.scrollHeight;
        chatArea.style.visibility = '';
        return;
      }

      timer = window.setTimeout(keepPinnedUntilStable, 80);
    };

    timer = window.setTimeout(keepPinnedUntilStable, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      chatArea.style.visibility = '';
    };
  }, [section, conversationReady, messages.length]);

'''

pattern = re.compile(
    r"  useEffect\(\(\) => \{\n"
    r"    if \(section !== 'chat' \|\| messages\.length === 0\) return undefined;.*?"
    r"  \}, \[section, messages\.length\]\);\n\n",
    re.S,
)
source, count = pattern.subn(new_effect, source, count=1)
if count != 1:
    raise RuntimeError('Não foi possível localizar com segurança o efeito atual de rolagem inicial.')

path.write_text(source, encoding='utf-8')