from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

helpers = r'''
  function normalizedPdfDecision(value = '') {
    return value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim()
      .toLowerCase();
  }

  function isExplicitPdfConfirmation(value = '') {
    const decision = normalizedPdfDecision(value);
    return [
      'quero o pdf',
      'pode gerar o pdf',
      'gere o pdf',
      'sim, quero o pdf',
      'sim quero o pdf',
      'pode criar o pdf',
      'crie o pdf',
    ].includes(decision);
  }

  function findLatestPdfOffer(items) {
    return [...items].reverse().find((message) => (
      message.role === 'assistant'
      && /pdf/i.test(message.text || '')
      && /(quer|posso|organizar|gerar|criar)/i.test(message.text || '')
    ));
  }

  async function generateConfirmedPdf(operationName, offerMessage) {
    const assistantSections = messages
      .filter((message) => message.role === 'assistant' && message.text?.trim() && !message.isError)
      .slice(-12)
      .map((message, index) => ({
        title: index === 0 ? 'Análise' : `Continuação ${index + 1}`,
        content: message.text.trim(),
      }));

    const response = await authorizedFetch('/api/reports/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        confirmed: true,
        title: operationName ? `Relatório DomnAI - ${operationName}` : 'Relatório personalizado DomnAI',
        operation: operationName || 'Análise geral',
        summary: offerMessage?.text || assistantSections.at(-1)?.content || 'Relatório solicitado pelo usuário.',
        sections: assistantSections,
        metrics: [],
        tables: [],
        charts: [],
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || 'Não foi possível gerar o PDF.');
    }

    const contentResponse = await authorizedFetch(payload.contentUrl);
    if (!contentResponse.ok) throw new Error('O PDF foi criado, mas não foi possível abri-lo agora.');
    const blob = await contentResponse.blob();

    return {
      id: `pdf-${payload.id}-${Date.now()}`,
      libraryId: payload.id,
      name: payload.name,
      type: 'pdf',
      mimeType: payload.mimeType,
      size: payload.sizeBytes,
      previewUrl: URL.createObjectURL(blob),
    };
  }

'''

marker = "  async function sendMessage(event) {"
if helpers.strip() not in source:
    if marker not in source:
        raise RuntimeError('Não foi possível localizar sendMessage para conectar o PDF.')
    source = source.replace(marker, helpers + marker, 1)

injection_target = """    const operationName = operations.find((item) => item.id === activeOperation)?.name || null;
    const messageForApi = text || `Analise os arquivos anexados: ${sentAttachments.map((item) => item.name).join(', ')}`;

    setMessages((current) => [...current, userMessage]);
"""

injection = """    const operationName = operations.find((item) => item.id === activeOperation)?.name || null;
    const messageForApi = text || `Analise os arquivos anexados: ${sentAttachments.map((item) => item.name).join(', ')}`;
    const pdfOffer = findLatestPdfOffer(messages);

    if (isExplicitPdfConfirmation(text) && pdfOffer) {
      setMessages((current) => [...current, userMessage]);
      setDraft('');
      setAttachments([]);
      setPlusOpen(false);
      setResponding(true);
      try {
        const pdfAttachment = await generateConfirmedPdf(operationName, pdfOffer);
        setMessages((current) => [...current, {
          id: Date.now() + 1,
          role: 'assistant',
          text: 'PDF criado e salvo na sua Biblioteca.',
          attachments: [pdfAttachment],
        }]);
        await loadLibrary();
      } catch (error) {
        setMessages((current) => [...current, {
          id: Date.now() + 1,
          role: 'assistant',
          text: error.message || 'Não foi possível gerar o PDF.',
          attachments: [],
          isError: true,
        }]);
      } finally {
        setResponding(false);
      }
      return;
    }

    setMessages((current) => [...current, userMessage]);
"""

if injection not in source:
    if injection_target not in source:
        raise RuntimeError('Não foi possível localizar o ponto de confirmação do PDF.')
    source = source.replace(injection_target, injection, 1)

source = source.replace(
    "openAttachment(item)",
    "openAttachment(item, item.libraryId ? '/api/library' : null)",
)

path.write_text(source, encoding='utf-8')
