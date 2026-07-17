from pathlib import Path
import re

ROOT = Path('/frontend/src')


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: esperado 1 trecho, encontrado {count}.')
    return source.replace(old, new, 1)


# 1) Plano FREE com créditos avulsos pode usar chat e operações enquanto houver saldo.
access_path = ROOT / 'dashboard-access-control.js'
access = access_path.read_text(encoding='utf-8')
access = replace_once(
    access,
    "    html.classList.toggle('domnai-access-unselected', !domnaiAccessStatus.plan || domnaiAccessStatus.plan === 'unselected');\n",
    "    html.classList.toggle('domnai-access-unselected', !domnaiAccessStatus.plan || domnaiAccessStatus.plan === 'unselected');\n"
    "    html.classList.toggle('domnai-access-credits', Number(domnaiAccessStatus.totalCredits || 0) > 0);\n",
    'classe de acesso por créditos avulsos',
)
access = replace_once(
    access,
    "  if (!document.documentElement.classList.contains('domnai-access-free')) return;\n",
    "  const html = document.documentElement;\n"
    "  if (!html.classList.contains('domnai-access-free') || html.classList.contains('domnai-access-credits')) return;\n",
    'liberação do FREE com saldo',
)
access = access.replace(
    'Assine o PREMIUM para utilizar operações, chat, arquivos, Biblioteca e Lixeira.',
    'Assine o PREMIUM ou compre créditos avulsos para utilizar as operações e o chat.',
)
access = access.replace(
    'Assine o PREMIUM para utilizar as operações e o chat.',
    'Assine o PREMIUM ou compre créditos avulsos para utilizar as operações e o chat.',
)
access_path.write_text(access, encoding='utf-8')


# 2 e 3) Faturamento: comunicar a cobrança real e separar envio de geração de arquivos.
billing_path = ROOT / 'dashboard-billing-enhancements.js'
billing = billing_path.read_text(encoding='utf-8')

billing = replace_once(
    billing,
    "      <li>Envio de PDF, link, print, imagem e documentos</li>\n      <li>Biblioteca e Lixeira</li>",
    "      <li>Envio de PDFs, imagens, links e documentos para análise</li>\n"
    "      <li>Geração de PDFs e planilhas pelo chat</li>\n"
    "      <li>Biblioteca e Lixeira</li>",
    'descrição correta das capacidades de arquivos',
)

billing = billing.replace(
    "'Navegação e visualização da plataforma.'",
    "'Navegação e visualização; chat e operações disponíveis com créditos avulsos.'",
)
billing = billing.replace(
    '<p>Navegação e visualização da plataforma.</p>',
    '<p>Navegação e visualização; use chat e operações ao comprar créditos avulsos.</p>',
)

old_rules = '''<section class="billing-rules-section"><div class="billing-section-title"><small>Consumo</small><h2>Créditos por utilização</h2></div><div class="billing-rules-grid"><span><strong>1 crédito</strong> Pergunta com resposta</span><span><strong>2 créditos</strong> Análise completa</span><span><strong>5 a 10 créditos</strong> PDF, link, print, imagem ou documento</span></div></section>'''
new_rules = '''<section class="billing-rules-section"><div class="billing-section-title"><small>Consumo</small><h2>Créditos por utilização</h2></div><div class="billing-rules-grid"><span><strong>A partir de 1 crédito</strong> Respostas, conforme o processamento utilizado</span><span><strong>7 créditos</strong> PDF gerado pelo chat</span><span><strong>7 créditos</strong> Planilha gerada pelo chat</span></div></section>'''
billing = replace_once(billing, old_rules, new_rules, 'tabela real de consumo de créditos')


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
    count = billing.count(marker)
    if count != 1:
        raise RuntimeError(f'auxiliar de escape do perfil: esperado 1 ponto, encontrado {count}.')
    billing = billing.replace(marker, escape_helper + marker, 1)

profile_fields = [
    'fullName', 'phone', 'cpf', 'birthDate', 'zipCode', 'street', 'number',
    'complement', 'lot', 'block', 'building', 'apartment', 'neighborhood', 'city', 'state',
]
for field in profile_fields:
    old = "${profile.%s || ''}" % field
    new = "${escapeHtmlAttribute(profile.%s)}" % field
    if new in billing:
        continue
    count = billing.count(old)
    if count != 1:
        raise RuntimeError(f'escape do campo {field}: esperado 1 trecho, encontrado {count}.')
    billing = billing.replace(old, new, 1)

billing_path.write_text(billing, encoding='utf-8')

print('Bloco 4 corrigido: FREE com saldo, cobrança real, capacidades claras e perfil escapado.')
