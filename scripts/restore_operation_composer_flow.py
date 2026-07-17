from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

replacement = '''  async function selectOperation(item) {
    if (responding) return;

    setAttachments([]);
    setSearch('');
    setSearchOpen(false);
    setOptionsOpen(false);
    setPlusOpen(false);
    setSidebarOpen(false);
    setSection('chat');

    try {
      const response = await authorizedFetch('/api/chat-state/new-operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active_operation: item.id, operation_name: item.name }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || 'Não foi possível iniciar uma nova operação.');
      }

      setMessages(Array.isArray(payload.messages) ? payload.messages : []);
      setActiveOperation(payload.activeOperation || item.id);
      setDraft(item.name);
      window.setTimeout(() => {
        setComposerScrollRequest((current) => current + 1);
      }, 120);
    } catch (error) {
      window.alert(error.message || 'Não foi possível iniciar uma nova operação.');
    }
  }'''

source, count = re.subn(
    r"  (?:async )?function selectOperation\(item\) \{.*?\n  \}",
    replacement,
    source,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError('Não foi possível restaurar o fluxo validado da operação para a caixa de mensagem.')

path.write_text(source, encoding='utf-8')
print('Fluxo validado restaurado: operação vai para a caixa e aceita envio com ou sem arquivo.')
