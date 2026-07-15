from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

old_response = '''      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: 'assistant',
        text: payload.reply || 'O DomnAI não retornou uma resposta em texto.',
        attachments: [],
      }]);'''

new_response = '''      const generatedArtifact = payload.artifact ? {
        id: `artifact-${payload.artifact.id}-${Date.now()}`,
        libraryId: payload.artifact.libraryId || payload.artifact.id,
        name: payload.artifact.name,
        type: payload.artifact.type || (payload.artifact.mimeType === 'application/pdf' ? 'pdf' : 'file'),
        artifactType: payload.artifact.artifactType || null,
        mimeType: payload.artifact.mimeType || '',
        size: payload.artifact.size || payload.artifact.sizeBytes || 0,
        contentUrl: payload.artifact.contentUrl || null,
      } : null;

      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: 'assistant',
        text: payload.reply || 'O DomnAI não retornou uma resposta em texto.',
        attachments: generatedArtifact ? [generatedArtifact] : [],
      }]);

      if (generatedArtifact) {
        await loadLibrary();
      }'''

# Fluxo legado: conecta o artefato diretamente à resposta síncrona.
if old_response in source:
    source = source.replace(old_response, new_response, 1)
# Fluxo persistente: os artefatos já chegam pelo polling em result.artifacts.
elif "async function pollChatTask(taskId)" not in source and "const generatedArtifact" not in source:
    raise RuntimeError('Não foi possível localizar um fluxo de resposta compatível para conectar os artefatos.')

# Mantém abertura autenticada de arquivos em mensagens e na Biblioteca.
source = source.replace(
    "openAttachment(item)",
    "openAttachment(item, item.libraryId ? '/api/library' : null)",
)

path.write_text(source, encoding='utf-8')
