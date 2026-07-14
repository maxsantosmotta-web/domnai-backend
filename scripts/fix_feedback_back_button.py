from pathlib import Path

FEEDBACK = Path('/frontend/src/dashboard-feedback.js')
MAIN = Path('/frontend/src/main.jsx')

feedback_source = FEEDBACK.read_text(encoding='utf-8')
button = '<button type="button" class="domnai-feedback-back">Voltar</button>'

if feedback_source.count(button) != 1:
    raise SystemExit('Botão Voltar do Feedback não encontrado exatamente uma vez após o refinamento.')

main_source = MAIN.read_text(encoding='utf-8')
old_import = "import './dashboard-sidebar-cleanup.css';\n"
new_import = "import './dashboard-sidebar-cleanup.css';\nimport './dashboard-feedback-back-fix.css';\n"

if main_source.count(old_import) != 1:
    raise SystemExit('Ponto de importação do ajuste do Feedback não encontrado exatamente uma vez.')

main_source = main_source.replace(old_import, new_import, 1)
MAIN.write_text(main_source, encoding='utf-8')

print('Voltar do Feedback exibido e menu de opções do chat isolado.')
