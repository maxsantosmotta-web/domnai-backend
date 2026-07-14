from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

ref_line = "  const initialBrowserScrollDoneRef = useRef(false);"
if ref_line not in source:
    marker = "  const chatScrollRef = useRef(null);"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o ref do container do chat.')
    source = source.replace(marker, marker + "\n" + ref_line, 1)

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
    chatArea.scrollTo({ top: 0, behavior: 'auto' });

    let cancelled = false;
    let lastHeight = -1;
    let stableChecks = 0;
    let checks = 0;
    let timer = null;

    const waitForFinalHeight = () => {
      if (cancelled) return;

      const currentHeight = chatArea.scrollHeight;
      stableChecks = currentHeight === lastHeight ? stableChecks + 1 : 0;
      lastHeight = currentHeight;
      checks += 1;

      if (stableChecks >= 4 || checks >= 24) {
        chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'smooth' });
        timer = window.setTimeout(() => {
          if (!cancelled) chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'auto' });
        }, 900);
        return;
      }

      timer = window.setTimeout(waitForFinalHeight, 100);
    };

    timer = window.setTimeout(waitForFinalHeight, 120);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
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
