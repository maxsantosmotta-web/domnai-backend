from pathlib import Path

path = Path('/frontend/src/main.jsx')
source = path.read_text(encoding='utf-8')

css_import = "import './dashboard-billing-back-compact.css';"
js_import = "import './dashboard-billing-back-text-fix.js';"

if css_import not in source:
    source = source.replace(
        "import './dashboard-billing-enhancements.css';",
        "import './dashboard-billing-enhancements.css';\n" + css_import,
        1,
    )

if js_import not in source:
    source = source.replace(
        "import './dashboard-billing-enhancements.js';",
        "import './dashboard-billing-enhancements.js';\n" + js_import,
        1,
    )

path.write_text(source, encoding='utf-8')
