from pathlib import Path

path = Path('/frontend/src/main.jsx')
source = path.read_text(encoding='utf-8')
import_line = "import './dashboard-billing-back-text-fix.js';"
if import_line not in source:
    source = source.replace(
        "import './dashboard-billing-enhancements.js';",
        "import './dashboard-billing-enhancements.js';\n" + import_line,
        1,
    )
path.write_text(source, encoding='utf-8')
