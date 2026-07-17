from pathlib import Path
import re

ROOT = Path('/frontend/src')


def ensure_once(source: str, marker: str, label: str) -> None:
    count = source.count(marker)
    if count != 1:
        raise RuntimeError(f'{label}: esperado 1 trecho, encontrado {count}.')


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

print('Bloco 4 corrigido: FREE com saldo, cobrança real, capacidades claras e perfil escapado.')
