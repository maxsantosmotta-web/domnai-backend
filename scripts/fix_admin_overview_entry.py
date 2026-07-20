from pathlib import Path
import re

TARGET = Path('/frontend/src/AdminAccessBoundary.jsx')

source = TARGET.read_text(encoding='utf-8')

css_marker = "import './admin-premium-monitor.css';\n"
css_import = "import './admin-overview-entry-fixes.css';\n"
if css_import not in source:
    if source.count(css_marker) != 1:
        raise SystemExit('Importação premium não encontrada exatamente uma vez.')
    source = source.replace(css_marker, css_marker + css_import, 1)

state_pattern = re.compile(
    r"const \[activeSection, setActiveSection\] = useState\(\(\) => \{\s*"
    r"const saved = sessionStorage\.getItem\('domnai:admin-section:v1'\);\s*"
    r"return .*?;\s*\}\);",
    re.S,
)
source, state_count = state_pattern.subn(
    "const [activeSection, setActiveSection] = useState('Visão geral');",
    source,
    count=1,
)
if state_count != 1:
    raise SystemExit(f'Estado persistente do módulo: esperado 1 trecho, encontrado {state_count}.')

source = source.replace(
    "    sessionStorage.setItem('domnai:admin-section:v1', section);\n",
    '',
    1,
)

old_user_button = '''          <button type="button" className="domnai-admin-user-menu-entry" onClick={onUser}>
             Painel Usuário
           </button>'''
new_user_button = '''          <button
             type="button"
             className="domnai-admin-user-menu-entry"
             onClick={() => {
               setActiveSection('Visão geral');
               sessionStorage.removeItem('domnai:admin-section:v1');
               onUser();
             }}
           >
             Painel Usuário
           </button>'''
if source.count(old_user_button) != 1:
    raise SystemExit(f'Botão Painel Usuário: esperado 1 trecho, encontrado {source.count(old_user_button)}.')
source = source.replace(old_user_button, new_user_button, 1)

TARGET.write_text(source, encoding='utf-8')

overview_target = Path('/frontend/src/AdminOverviewView.jsx')
overview = overview_target.read_text(encoding='utf-8')

replacements = [
    (
        "  cutover: {},\n};",
        "  cutover: {},\n  shadow: {},\n};",
        'estado shadow',
    ),
    (
        "        ['cutover', '/api/admin/cutover?limit=1000', authorizedHeaders],\n        ['health', '/health', {}],",
        "        ['cutover', '/api/admin/cutover?limit=1000', authorizedHeaders],\n        ['shadow', '/api/admin/shadow-validation?limit=1000', authorizedHeaders],\n        ['health', '/health', {}],",
        'requisição shadow',
    ),
    (
        "  const cutoverSummary = data.cutover?.summary || {};",
        "  const cutoverSummary = data.cutover?.summary || {};\n  const shadowSummary = data.shadow?.summary || {};",
        'resumo shadow',
    ),
    (
        "          <article data-tone={data.cutover?.shadowApproved ? 'green' : 'gold'}><span>Validação shadow</span><strong>{data.cutover?.shadowApproved ? 'Aprovada' : 'Pendente'}</strong><small>{data.cutover?.requireShadowApproval ? 'aprovação obrigatória' : 'aprovação não exigida'}</small></article>",
        "          <article data-tone={shadowSummary.approved ? 'green' : 'gold'}><span>Validação shadow</span><strong>{shadowSummary.approved ? 'Aprovada' : 'Pendente'}</strong><small>{formatPercent(shadowSummary.success_rate)} de sucesso</small></article>",
        'status shadow',
    ),
    (
        "          <article data-tone=\"purple\"><span>Amostras</span><strong>{formatNumber(cutoverSummary.sampleCount)}</strong><small>{formatNumber(cutoverSummary.newCoreResponses)} respostas do novo núcleo</small></article>",
        "          <article data-tone=\"purple\"><span>Amostras shadow</span><strong>{formatNumber(shadowSummary.sample_count)}</strong><small>{formatPercent(shadowSummary.non_empty_rate)} respostas não vazias · {formatPercent(shadowSummary.average_similarity)} similaridade</small></article>",
        'amostras shadow',
    ),
]

for old, new, label in replacements:
    if old not in overview:
        if new in overview:
            continue
        raise SystemExit(f'{label}: trecho esperado não encontrado.')
    overview = overview.replace(old, new, 1)

overview_target.write_text(overview, encoding='utf-8')
print('Visão geral definida como entrada obrigatória e métricas shadow reais conectadas ao painel.')