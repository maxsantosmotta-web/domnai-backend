from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

new_effect = r'''  useEffect(() => {
    if (
      section !== 'chat'
      || !conversationReady
      || messages.length === 0
      || initialBrowserScrollDoneRef.current
    ) return undefined;

    const chatArea = chatScrollRef.current;
    if (!chatArea) return undefined;

    initialBrowserScrollDoneRef.current = true;

    let cancelled = false;
    let lastHeight = -1;
    let stableChecks = 0;
    let checks = 0;
    let timer = null;

    const openAtFinalBottom = () => {
      if (cancelled) return;

      const currentHeight = chatArea.scrollHeight;
      stableChecks = currentHeight === lastHeight ? stableChecks + 1 : 0;
      lastHeight = currentHeight;
      checks += 1;

      if (stableChecks >= 4 || checks >= 24) {
        chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'auto' });
        return;
      }

      timer = window.setTimeout(openAtFinalBottom, 100);
    };

    timer = window.setTimeout(openAtFinalBottom, 120);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [section, conversationReady, messages.length]);

'''

pattern = re.compile(
    r"  useEffect\(\(\) => \{\n"
    r"    if \(\n"
    r"      section !== 'chat'.*?"
    r"  \}, \[section, conversationReady, messages\.length\]\);\n\n",
    re.S,
)
source, count = pattern.subn(new_effect, source, count=1)
if count != 1:
    raise RuntimeError('Não foi possível localizar com segurança o efeito de rolagem do navegador.')

path.write_text(source, encoding='utf-8')
