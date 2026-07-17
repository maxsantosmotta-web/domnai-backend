from pathlib import Path
import re

ROOT = Path('/frontend/src')


def ensure_once(source: str, marker: str, label: str) -> None:
    count = source.count(marker)
    if count != 1:
        raise RuntimeError(f'{label}: esperado 1 trecho, encontrado {count}.')


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if old in source:
        return source.replace(old, new, 1)
    if new in source:
        return source
    raise RuntimeError(f'{label}: trecho esperado não encontrado.')


# 1) Plano FREE com créditos avulsos pode usar chat e operações enquanto houver saldo.
access_path = ROOT / 'dashboard-access-control.js'
access = access_path.read_text(encoding='utf-8')

credits_line = "    html.classList.toggle('domnai-access-credits', Number(domnaiAccessStatus.totalCredits || 0) > 0);"
if credits_line not in access:
    pattern = re.compile(r"^(\s*html\.classList\.toggle\('domnai-access-unselected'.*?\);)\s*$", re.M)
    access, count = pattern.subn(r"\1\n" + credits_line, access, count=1)
    if count != 1:
        raise RuntimeError(f'classe de acesso por créditos avulsos: esperado 1 trecho, encontrado {count}.')

new_block_guard = "  const html = document.documentElement;\n  if (!html.classList.contains('domnai-access-free') || html.classList.contains('domnai-access-credits')) return;"
if new_block_guard not in access:
    pattern = re.compile(r"\s*if \(!document\.documentElement\.classList\.contains\('domnai-access-free'\)\) return;")
    access, count = pattern.subn("\n" + new_block_guard, access, count=1)
    if count != 1:
        raise RuntimeError(f'liberação do FREE com saldo: esperado 1 trecho, encontrado {count}.')

for old_text in (
    'Assine o PREMIUM para utilizar operações, chat, arquivos, Biblioteca e Lixeira.',
    'Assine o PREMIUM para utilizar as operações e o chat.',
):
    access = access.replace(
        old_text,
        'Assine o PREMIUM ou compre créditos avulsos para utilizar as operações e o chat.',
    )

access_path.write_text(access, encoding='utf-8')


# 2 e 3) Faturamento: comunicar a cobrança real e separar envio de geração de arquivos.
billing_path = ROOT / 'dashboard-billing-enhancements.js'
billing = billing_path.read_text(encoding='utf-8')

new_capabilities = (
    '      <li>Envio de PDFs, imagens, links e documentos para análise</li>\n'
    '      <li>Geração de PDFs e planilhas pelo chat</li>\n'
    '      <li>Biblioteca e Lixeira</li>'
)
if 'Geração de PDFs e planilhas pelo chat' not in billing:
    pattern = re.compile(
        r"\s*<li>Envio de PDF, link, print, imagem e documentos</li>\s*"
        r"<li>Biblioteca e Lixeira</li>"
    )
    billing, count = pattern.subn("\n" + new_capabilities, billing, count=1)
    if count != 1:
        raise RuntimeError(f'descrição correta das capacidades de arquivos: esperado 1 trecho, encontrado {count}.')

billing = billing.replace(
    "'Navegação e visualização da plataforma.'",
    "'Navegação e visualização; chat e operações disponíveis com créditos avulsos.'",
)
billing = billing.replace(
    '<p>Navegação e visualização da plataforma.</p>',
    '<p>Navegação e visualização; use chat e operações ao comprar créditos avulsos.</p>',
)

new_rules = '<section class="billing-rules-section"><div class="billing-section-title"><small>Consumo</small><h2>Créditos por utilização</h2></div><div class="billing-rules-grid"><span><strong>A partir de 1 crédito</strong> Respostas, conforme o processamento utilizado</span><span><strong>7 créditos</strong> PDF gerado pelo chat</span><span><strong>7 créditos</strong> Planilha gerada pelo chat</span></div></section>'
if 'Respostas, conforme o processamento utilizado' not in billing:
    pattern = re.compile(r'<section class="billing-rules-section">.*?</section>', re.S)
    billing, count = pattern.subn(new_rules, billing, count=1)
    if count != 1:
        raise RuntimeError(f'tabela real de consumo de créditos: esperado 1 trecho, encontrado {count}.')


# 4) Escapar dados persistidos antes de inseri-los em atributos HTML do formulário.
escape_helper = '''function escapeHtmlAttribute(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

'''
if 'function escapeHtmlAttribute(value)' not in billing:
    marker = 'function formatCpf(value) {'
    ensure_once(billing, marker, 'auxiliar de escape do perfil')
    billing = billing.replace(marker, escape_helper + marker, 1)

profile_pattern = re.compile(r"\$\{profile\.([A-Za-z0-9_]+)\s*\|\|\s*''\}")
fields_found = set(profile_pattern.findall(billing))
required_fields = {
    'fullName', 'phone', 'cpf', 'birthDate', 'zipCode', 'street', 'number',
    'complement', 'lot', 'block', 'building', 'apartment', 'neighborhood', 'city', 'state',
}
already_escaped = {
    field for field in required_fields
    if f'${{escapeHtmlAttribute(profile.{field})}}' in billing
}
missing = required_fields - fields_found - already_escaped
if missing:
    raise RuntimeError('campos de perfil não encontrados para escape: ' + ', '.join(sorted(missing)))

billing = profile_pattern.sub(lambda match: '${escapeHtmlAttribute(profile.%s)}' % match.group(1), billing)
billing_path.write_text(billing, encoding='utf-8')


# 5) Falhas do chat/artefatos: mensagem em português e repetição com o mesmo snapshot.
dashboard_path = ROOT / 'Dashboard.jsx'
dashboard = dashboard_path.read_text(encoding='utf-8')

friendly_helper = '''  function friendlyChatError(error, fallback = 'Não foi possível concluir esta operação.') {
    const raw = String(error?.message || error || '').trim();
    const normalized = raw.toLowerCase();
    if (!raw || normalized === 'failed to fetch' || normalized.includes('networkerror') || normalized.includes('load failed')) {
      return 'Não foi possível conectar ao DomnAI. Verifique sua conexão e tente novamente.';
    }
    if (normalized.includes('timeout') || normalized.includes('tempo limite')) {
      return 'A operação demorou mais que o esperado. Tente novamente.';
    }
    return raw;
  }

'''
if 'function friendlyChatError(error' not in dashboard:
    marker = '  async function pollChatTask(taskId) {'
    ensure_once(dashboard, marker, 'ponto do tradutor de falhas')
    dashboard = dashboard.replace(marker, friendly_helper + marker, 1)

dashboard = dashboard.replace(
    "text: error.message || 'Não foi possível acompanhar a resposta.',",
    "text: friendlyChatError(error, 'Não foi possível acompanhar a resposta.'),",
)
dashboard = dashboard.replace(
    "text: error.message || 'Não foi possível concluir a análise. Tente novamente.',",
    "text: friendlyChatError(error, 'Não foi possível concluir a análise. Tente novamente.'),",
)
dashboard = dashboard.replace(
    "text: error.message || 'Não foi possível tentar novamente.',",
    "text: friendlyChatError(error, 'Não foi possível tentar novamente.'),",
)

dashboard = replace_once(
    dashboard,
    '''    const operationName = operations.find((item) => item.id === activeOperation)?.name || null;
    const messageForApi = text || `Analise os arquivos anexados: ${sentAttachments.map((item) => item.name).join(', ')}`;

    setMessages((current) => [...current, userMessage]);''',
    '''    const operationName = operations.find((item) => item.id === activeOperation)?.name || null;
    const messageForApi = text || `Analise os arquivos anexados: ${sentAttachments.map((item) => item.name).join(', ')}`;
    const requestSnapshot = {
      message: messageForApi,
      operation: operationName,
      history,
      attachments: sentAttachments
        .filter((item) => item.libraryId)
        .map((item) => ({ library_id: item.libraryId })),
    };
    userMessage.requestSnapshot = requestSnapshot;

    setMessages((current) => [...current, userMessage]);''',
    'snapshot da solicitação atual',
)

dashboard = replace_once(
    dashboard,
    '''          body: JSON.stringify({
            message: messageForApi,
            operation: operationName,
            history,
            attachments: sentAttachments
              .filter((item) => item.libraryId)
              .map((item) => ({ library_id: item.libraryId })),
          }),''',
    '''          body: JSON.stringify(requestSnapshot),''',
    'envio pelo snapshot',
)

dashboard = replace_once(
    dashboard,
    '''          taskId,
          processing: true,
          isError: false,''',
    '''          taskId,
          requestSnapshot,
          processing: true,
          isError: false,''',
    'snapshot na resposta em processamento',
)

dashboard = replace_once(
    dashboard,
    '''        attachments: [],
        isError: true,
        processing: false,''',
    '''        attachments: [],
        requestSnapshot,
        isError: true,
        processing: false,''',
    'snapshot na falha inicial',
)

dashboard = replace_once(
    dashboard,
    '''        taskId: message.taskId || null,
        processing: Boolean(message.processing),''',
    '''        taskId: message.taskId || null,
        requestSnapshot: message.requestSnapshot || null,
        processing: Boolean(message.processing),''',
    'persistência do snapshot',
)

dashboard = replace_once(
    dashboard,
    '''    const errorMessage = messages[errorIndex];
    const userMessage = messages[userIndex];
    const originalTaskId = errorMessage.taskId || userMessage.taskId || null;
    const messageForApi = String(userMessage.text || '').trim()
      || `Analise os arquivos anexados: ${(userMessage.attachments || []).map((item) => item.name).join(', ')}`;
    if (!messageForApi) return;''',
    '''    const errorMessage = messages[errorIndex];
    const userMessage = messages[userIndex];
    const originalTaskId = errorMessage.taskId || userMessage.taskId || null;
    const savedSnapshot = errorMessage.requestSnapshot || userMessage.requestSnapshot || null;
    const messageForApi = String(savedSnapshot?.message || userMessage.text || '').trim()
      || `Analise os arquivos anexados: ${(userMessage.attachments || []).map((item) => item.name).join(', ')}`;
    if (!messageForApi) return;''',
    'recuperação do snapshot na nova tentativa',
)

dashboard = replace_once(
    dashboard,
    '''    const operationName = operations.find((item) => item.id === activeOperation)?.name || null;
    setResponding(true);''',
    '''    const operationName = savedSnapshot?.operation ?? operations.find((item) => item.id === activeOperation)?.name ?? null;
    const retrySnapshot = savedSnapshot || {
      message: messageForApi,
      operation: operationName,
      history,
      attachments: (userMessage.attachments || [])
        .filter((item) => item.libraryId)
        .map((item) => ({ library_id: item.libraryId })),
    };
    setResponding(true);''',
    'snapshot exato da nova tentativa',
)

dashboard = replace_once(
    dashboard,
    '''            body: JSON.stringify({
              message: messageForApi,
              operation: operationName,
              history,
              attachments: (userMessage.attachments || [])
                .filter((item) => item.libraryId)
                .map((item) => ({ library_id: item.libraryId })),
            }),''',
    '''            body: JSON.stringify(retrySnapshot),''',
    'reenvio exato da operação',
)

dashboard = dashboard.replace(
    '''            taskId: originalTaskId,
            processing: true,''',
    '''            taskId: originalTaskId,
            requestSnapshot: retrySnapshot,
            processing: true,''',
    1,
)

dashboard_path.write_text(dashboard, encoding='utf-8')

print('Bloco 4 corrigido: acesso, cobrança, perfil, contexto de artefatos e falhas em português.')
