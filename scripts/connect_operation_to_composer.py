from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

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
        text: item.name,
        operationId: item.id,
        attachments: [],
      }]);
    }
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

path.write_text(source, encoding='utf-8')
