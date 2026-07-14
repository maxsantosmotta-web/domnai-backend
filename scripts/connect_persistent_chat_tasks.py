from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

# Idempotência: não altera novamente quando a fila já estiver conectada.
if "authorizedFetch('/api/chat/tasks'" in source:
    path.write_text(source, encoding='utf-8')
    raise SystemExit(0)

start_marker = "      const response = await authorizedFetch('/api/chat/respond', {"
end_marker = "    } catch (error) {"
start = source.find(start_marker)
end = source.find(end_marker, start)

if start == -1 or end == -1:
    raise RuntimeError('Fluxo atual do chat não foi localizado para conexão persistente.')

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
      }]);
'''

source = source[:start] + replacement + source[end:]
path.write_text(source, encoding='utf-8')
