from pathlib import Path

TARGET = Path('/frontend/src/main.jsx')
IMPORT_LINE = "import './interaction-button-states.css';\n"
JS_MARKER = "import './dashboard-link-enhancements.js';\n"

source = TARGET.read_text(encoding='utf-8')

if IMPORT_LINE not in source:
    if source.count(JS_MARKER) != 1:
        raise SystemExit('Ponto final das importações CSS não encontrado exatamente uma vez.')
    source = source.replace(JS_MARKER, IMPORT_LINE + JS_MARKER, 1)
    TARGET.write_text(source, encoding='utf-8')

print('Estados de toque dos botões carregados após todos os estilos do Dashboard.')
