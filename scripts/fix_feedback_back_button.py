from pathlib import Path

FEEDBACK = Path('/frontend/src/dashboard-feedback.js')
MAIN = Path('/frontend/src/main.jsx')

feedback_source = FEEDBACK.read_text(encoding='utf-8')
button = '<button type="button" class="domnai-feedback-back">Voltar</button>'
opening = '''    <section class="internal-section domnai-feedback-page" data-domnai-feedback-page="true">
      <header class="domnai-feedback-header">'''
opening_replacement = '''    <section class="internal-section domnai-feedback-page" data-domnai-feedback-page="true">
      <div class="domnai-feedback-dialog" role="dialog" aria-modal="true" aria-labelledby="domnai-feedback-title">
      <header class="domnai-feedback-header">'''
heading = '<h1>Feedback</h1>'
heading_replacement = '<h1 id="domnai-feedback-title">Feedback</h1>'
closing = '''      <section class="domnai-feedback-history-card" hidden>
        <div class="domnai-feedback-history-list" aria-live="polite"></div>
      </section>
    </section>
  `;'''
closing_replacement = '''      <section class="domnai-feedback-history-card" hidden>
        <div class="domnai-feedback-history-list" aria-live="polite"></div>
      </section>
      </div>
    </section>
  `;'''

checks = {
    'Botão Voltar': (button, 1),
    'Abertura da tela': (opening, 1),
    'Título do Feedback': (heading, 1),
    'Fechamento da tela': (closing, 1),
}

for label, (snippet, expected) in checks.items():
    count = feedback_source.count(snippet)
    if count != expected:
        raise SystemExit(f'{label}: esperado {expected} trecho, encontrado {count}.')

feedback_source = feedback_source.replace(opening, opening_replacement, 1)
feedback_source = feedback_source.replace(heading, heading_replacement, 1)
feedback_source = feedback_source.replace(closing, closing_replacement, 1)
FEEDBACK.write_text(feedback_source, encoding='utf-8')

main_source = MAIN.read_text(encoding='utf-8')
old_import = "import './dashboard-sidebar-cleanup.css';\n"
new_import = "import './dashboard-sidebar-cleanup.css';\nimport './dashboard-feedback-back-fix.css';\n"

if main_source.count(old_import) != 1:
    raise SystemExit('Ponto de importação do ajuste do Feedback não encontrado exatamente uma vez.')

main_source = main_source.replace(old_import, new_import, 1)
MAIN.write_text(main_source, encoding='utf-8')

print('Feedback estruturado como modal horizontal centralizado.')
