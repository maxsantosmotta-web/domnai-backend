from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

pattern = re.compile(
    r"      const response = await authorizedFetch\('/api/chat/respond', \{.*?"
    r"      setMessages\(\(current\) => \[\.\.\.current, \{\n"
    r"        id: Date\.now\(\) \+ 1,\n"
    r"        role: 'assistant',\n"
    r"        text: payload\.reply \|\| 'O DomnAI não retornou uma resposta em texto\.',\n"
    r"        attachments: \[\],\n"
    r"      \}\]\);",
    re.S,
)

replacement = '''      const createResponse = await authorizedFetch('/api/chat/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageForApi,
          operation: operationName,
          history,
          attachment_ids: sentAttachments.map((item) => item.libraryId).filter(Boolean),
        }),
      });
      const created = await createResponse.json().catch(() => ({}));
      if (!createResponse.ok) {
        throw new Error(created.detail || 'Não foi possível iniciar a resposta do DomnAI.');
      }

      const taskId = created.taskId;
      let taskPayload = created;
      while (!['completed', 'failed'].includes(taskPayload.status)) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        const statusResponse = await authorizedFetch(`/api/chat/tasks/${taskId}`);
        taskPayload = await statusResponse.json().catch(() => ({}));
        if (!statusResponse.ok) {
          throw new Error(taskPayload.detail || 'Não foi possível acompanhar a resposta do DomnAI.');
        }
      }
      if (taskPayload.status === 'failed') {
        throw new Error(taskPayload.error || 'Não foi possível concluir a resposta.');
      }

      const result = taskPayload.result || {};
      const sourceText = Array.isArray(result.sources) && result.sources.length
        ? `\n\nFontes consultadas:\n${result.sources.map((item, index) => `${index + 1}. ${item.title || item.url} — ${item.url}`).join('\n')}`
        : '';
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: 'assistant',
        text: `${result.reply || 'O DomnAI não retornou uma resposta em texto.'}${sourceText}`,
        attachments: Array.isArray(result.artifacts) ? result.artifacts : [],
      }]);'''

source, count = pattern.subn(replacement, source, count=1)
if count != 1:
    raise RuntimeError('Fluxo atual do chat não foi localizado para conexão persistente.')

path.write_text(source, encoding='utf-8')
