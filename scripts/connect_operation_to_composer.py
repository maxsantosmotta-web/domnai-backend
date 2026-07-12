from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

if "const operationComposerRef = useRef(null);" not in source:
    source = source.replace(
        "  const fileInputRef = useRef(null);",
        "  const fileInputRef = useRef(null);\n  const operationComposerRef = useRef(null);\n  const [composerScrollRequest, setComposerScrollRequest] = useState(0);",
        1,
    )

scroll_effect = '''
  useEffect(() => {
    if (!composerScrollRequest || section !== 'chat') return undefined;

    let cancelled = false;
    let secondFrame = null;

    const moveToComposer = () => {
      if (cancelled) return;

      const chatArea = document.querySelector('.clean-chat-area');
      if (chatArea) {
        chatArea.scrollTop = chatArea.scrollHeight;
      }

      const composer = operationComposerRef.current;
      if (!composer) return;

      composer.scrollIntoView({ behavior: 'auto', block: 'end', inline: 'nearest' });

      const pageScroller = document.scrollingElement || document.documentElement;
      pageScroller.scrollTop = pageScroller.scrollHeight;
      window.scrollTo(0, pageScroller.scrollHeight);
    };

    const firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(moveToComposer);
    });
    const settleTimer = window.setTimeout(moveToComposer, 180);
    const finalTimer = window.setTimeout(moveToComposer, 420);

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(firstFrame);
      if (secondFrame !== null) window.cancelAnimationFrame(secondFrame);
      window.clearTimeout(settleTimer);
      window.clearTimeout(finalTimer);
    };
  }, [composerScrollRequest, section, messages.length]);

'''

if "[composerScrollRequest, section, messages.length]" not in source:
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

form_old = '<form className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
form_new = '<form ref={operationComposerRef} className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>'
if form_old not in source:
    raise RuntimeError('Não foi possível conectar a rolagem à caixa de envio.')
source = source.replace(form_old, form_new, 1)

path.write_text(source, encoding='utf-8')
