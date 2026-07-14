from pathlib import Path

path = Path('/frontend/src/main.jsx')
source = path.read_text(encoding='utf-8')

import_marker = "import App from './App';"
admin_import = "import AdminAccessBoundary from './AdminAccessBoundary';"

if admin_import not in source:
    if import_marker not in source:
        raise RuntimeError('Não foi possível localizar a importação principal do App.')
    source = source.replace(import_marker, f"{import_marker}\n{admin_import}", 1)

app_marker = "          <App />"
wrapped_app = "          <AdminAccessBoundary>\n            <App />\n          </AdminAccessBoundary>"

if wrapped_app not in source:
    if app_marker not in source:
        raise RuntimeError('Não foi possível localizar o ponto de montagem do App.')
    source = source.replace(app_marker, wrapped_app, 1)

path.write_text(source, encoding='utf-8')
