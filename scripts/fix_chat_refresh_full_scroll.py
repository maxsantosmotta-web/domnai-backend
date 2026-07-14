from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

helper = r'''
  function scrollConversationFromTopToBottom() {
    const chatArea = chatScrollRef.current;
    if (!chatArea) return;

    chatArea.scrollTo({ top: 0, behavior: 'auto' });
    window.requestAnimationFrame(() => {
      window.setTimeout(() => {
        chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'smooth' });
      }, 90);
    });
  }

'''

if 'function scrollConversationFromTopToBottom()' not in source:
    marker = '  function refreshConversation() {'
    if marker not in source:
        raise RuntimeError('Não foi possível localizar refreshConversation.')
    source = source.replace(marker, helper + marker, 1)

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
      window.setTimeout(scrollConversationFromTopToBottom, 140);
    } catch (error) {
      window.alert(error.message || 'Não foi possível atualizar a conversa.');
    }
  }'''

source, count = re.subn(
    r'  function refreshConversation\(\) \{.*?\n  \}',
    new_refresh,
    source,
    count=1,
    flags=re.S,
)
if count != 1:
    source, count = re.subn(
        r'  async function refreshConversation\(\) \{.*?\n  \}',
        new_refresh,
        source,
        count=1,
        flags=re.S,
    )
if count != 1:
    raise RuntimeError('Não foi possível substituir refreshConversation.')

# Troca o salto imediato por uma descida visível e completa após o histórico carregar.
source = source.replace(
    "    const scrollToLatest = () => {\n      chatArea.scrollTop = chatArea.scrollHeight;\n    };\n\n    scrollToLatest();\n    const frame = window.requestAnimationFrame(scrollToLatest);\n    const shortTimer = window.setTimeout(scrollToLatest, 120);\n    const settleTimer = window.setTimeout(scrollToLatest, 360);",
    "    const scrollToLatest = () => {\n      chatArea.scrollTo({ top: 0, behavior: 'auto' });\n      window.requestAnimationFrame(() => {\n        chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: 'smooth' });\n      });\n    };\n\n    const frame = window.requestAnimationFrame(() => {});\n    const shortTimer = window.setTimeout(scrollToLatest, 140);\n    const settleTimer = window.setTimeout(scrollToLatest, 520);",
    1,
)

path.write_text(source, encoding='utf-8')
