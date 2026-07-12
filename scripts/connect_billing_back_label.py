from pathlib import Path

path = Path('/frontend/src/main.jsx')
source = path.read_text(encoding='utf-8')

css_imports = [
    "import './dashboard-billing-back-compact.css';",
    "import './dashboard-module-back-buttons.css';",
    "import './dashboard-billing-instant-shell.css';",
]
js_imports = [
    "import './dashboard-billing-back-text-fix.js';",
    "import './dashboard-module-back-buttons.js';",
    "import './dashboard-billing-instant-shell.js';",
]

for css_import in css_imports:
    if css_import not in source:
        source = source.replace(
            "import './dashboard-billing-enhancements.css';",
            "import './dashboard-billing-enhancements.css';\n" + css_import,
            1,
        )

for js_import in js_imports:
    if js_import not in source:
        source = source.replace(
            "import './dashboard-billing-enhancements.js';",
            "import './dashboard-billing-enhancements.js';\n" + js_import,
            1,
        )

path.write_text(source, encoding='utf-8')
