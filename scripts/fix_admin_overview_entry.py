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
if state_count != 1 and "const [activeSection, setActiveSection] = useState('Visão geral');" not in source:
    raise SystemExit(f'Estado persistente do módulo: esperado trecho antigo ou final, encontrado {state_count}.')

source = source.replace(
    "    sessionStorage.setItem('domnai:admin-section:v1', section);\n",
    '',
    1,
)

# O botão de retorno ao Painel Usuário já é montado pelos patches anteriores do build.
# Este script cuida somente da entrada da Visão geral e das métricas shadow.
TARGET.write_text(source, encoding='utf-8')

overview_target = Path('/frontend/src/AdminOverviewView.jsx')
overview = overview_target.read_text(encoding='utf-8')

replacements = [
    (
        ("  cutover: {},\n};",),
        "  cutover: {},\n  shadow: {},\n};",
        'estado shadow',
    ),
    (
        ("        ['cutover', '/api/admin/cutover?limit=1000', authorizedHeaders],\n        ['health', '/health', {}],",),
        "        ['cutover', '/api/admin/cutover?limit=1000', authorizedHeaders],\n        ['shadow', '/api/admin/shadow-validation?limit=1000', authorizedHeaders],\n        ['health', '/health', {}],",
        'requisição shadow',
    ),
    (
        ("  const cutoverSummary = data.cutover?.summary || {};",),
        "  const cutoverSummary = data.cutover?.summary || {};\n  const shadowSummary = data.shadow?.summary || {};",
        'resumo shadow',
    ),
    (
        (
            "          <article data-tone={data.cutover?.shadowApproved ? 'green' : 'gold'}><span>Validação shadow</span><strong>{data.cutover?.shadowApproved ? 'Aprovada' : 'Pendente'}</strong><small>{data.cutover?.requireShadowApproval ? 'aprovação obrigatória' : 'aprovação não exigida'}</small></article>",
            "          <article data-tone={shadowSummary.approved ? 'green' : 'gold'}><span>Validação shadow</span><strong>{shadowSummary.approved ? 'Aprovada' : 'Pendente'}</strong><small>{formatPercent(shadowSummary.success_rate)} de sucesso</small></article>",
            "          <article data-tone={shadowSummary.approved ? 'green' : 'gold'}><span>Validação comportamental</span><strong>{shadowSummary.approved ? 'Aprovada' : 'Pendente'}</strong><small>{formatPercent(shadowSummary.behavior_adherence_rate)} de aderência · meta 100%</small></article>",
        ),
        "          <article data-tone={shadowSummary.approved ? 'green' : 'gold'}><span>Validação comportamental</span><strong>{shadowSummary.approved ? 'Aprovada' : 'Pendente'}</strong><small>{formatPercent(shadowSummary.behavior_adherence_rate)} de aderência · meta 100%{shadowSummary.top_behavior_failure ? ` · falha: ${shadowSummary.top_behavior_failure}` : ''}</small></article>",
        'status comportamental',
    ),
    (
        (
            "          <article data-tone=\"purple\"><span>Amostras</span><strong>{formatNumber(cutoverSummary.sampleCount)}</strong><small>{formatNumber(cutoverSummary.newCoreResponses)} respostas do novo núcleo</small></article>",
            "          <article data-tone=\"purple\"><span>Amostras shadow</span><strong>{formatNumber(shadowSummary.sample_count)}</strong><small>{formatPercent(shadowSummary.non_empty_rate)} respostas não vazias · {formatPercent(shadowSummary.average_similarity)} similaridade</small></article>",
        ),
        "          <article data-tone=\"purple\"><span>Amostras comportamentais</span><strong>{formatNumber(shadowSummary.sample_count)}</strong><small>{formatPercent(shadowSummary.non_empty_rate)} não vazias · {formatPercent(shadowSummary.average_behavior_score)} qualidade média</small></article>",
        'amostras comportamentais',
    ),
]

for old_options, new, label in replacements:
    if new in overview:
        continue
    matched = next((old for old in old_options if old in overview), None)
    if matched is None:
        raise SystemExit(f'{label}: trecho esperado não encontrado.')
    overview = overview.replace(matched, new, 1)

overview_target.write_text(overview, encoding='utf-8')
print('Painel conectado à validação comportamental v2 com identificação do critério mais recorrente.')
