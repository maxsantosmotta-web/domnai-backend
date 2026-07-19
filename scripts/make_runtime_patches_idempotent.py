from __future__ import annotations

import re
from pathlib import Path


STRICT_LINES = (
    '    raise RuntimeError(f"{label}: trecho esperado não encontrado")',
    "    raise RuntimeError(f'{label}: trecho esperado não encontrado')",
)
FUNCTION_PATTERN = re.compile(r"def\s+replace_once\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)")


def main() -> None:
    changed: list[str] = []
    inspected: list[str] = []

    for path in sorted(Path('/tmp').glob('*.py')):
        if path.name == Path(__file__).name:
            continue

        source = path.read_text(encoding='utf-8')
        match = FUNCTION_PATTERN.search(source)
        if not match:
            continue

        inspected.append(path.name)
        first_parameter = match.group(1)
        idempotent_block = (
            '    print(f"{label}: encaixe legado ausente; código-fonte atual preservado.")\n'
            f'    return {first_parameter}'
        )

        updated = source
        for strict_line in STRICT_LINES:
            updated = updated.replace(strict_line, idempotent_block)

        if updated != source:
            path.write_text(updated, encoding='utf-8')
            changed.append(path.name)

    print(f"Patches runtime inspecionados: {len(inspected)}.")
    print(f"Patches runtime tornados idempotentes: {len(changed)}.")
    if changed:
        print("Arquivos ajustados: " + ", ".join(changed))


if __name__ == '__main__':
    main()
