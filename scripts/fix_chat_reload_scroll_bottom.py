from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

ref_line = "  const chatScrollRef = useRef(null);"
if ref_line not in source:
    marker = "  const fileInputRef = useRef(null);"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar os refs do Dashboard.')
    source = source.replace(marker, marker + "\n" + ref_line, 1)

# Mantém a restauração de rolagem do navegador desativada somente enquanto o Dashboard está montado.
scroll_effect = r'''
  useEffect(() => {
    if (section !== 'chat') return undefined;

    const previousRestoration = window.history.scrollRestoration;
    window.history.scrollRestoration = 'manual';

    return () => {
      window.history.scrollRestoration = previousRestoration;
    };
  }, [section]);

  useEffect(() => {
    if (section !== 'chat' || messages.length === 0) return undefined;

    const chatArea = chatScrollRef.current;
    if (!chatArea) return undefined;

    const scrollToLatest = () => {
      chatArea.scrollTop = chatArea.scrollHeight;
    };

    scrollToLatest();
    const frame = window.requestAnimationFrame(scrollToLatest);
    const shortTimer = window.setTimeout(scrollToLatest, 120);
    const settleTimer = window.setTimeout(scrollToLatest, 360);

    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(shortTimer);
      window.clearTimeout(settleTimer);
    };
  }, [section, messages.length]);

'''

if "window.history.scrollRestoration = 'manual'" not in source:
    marker = "  function selectOperation(item) {"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o ponto seguro antes da seleção de operação.')
    source = source.replace(marker, scroll_effect + marker, 1)

old_chat_area = '<div className="chat-messages clean-chat-area">'
new_chat_area = '<div ref={chatScrollRef} className="chat-messages clean-chat-area">'
if old_chat_area in source:
    source = source.replace(old_chat_area, new_chat_area, 1)
elif new_chat_area not in source:
    raise RuntimeError('Não foi possível localizar o container de mensagens do chat.')

path.write_text(source, encoding='utf-8')
