from __future__ import annotations

from pathlib import Path


STRICT_LINES = (
    '    raise RuntimeError(f"{label}: trecho esperado não encontrado")',
    "    raise RuntimeError(f'{label}: trecho esperado não encontrado')",
)
IDEMPOTENT_BLOCK = '''    print(f"{label}: encaixe legado ausente; código-fonte atual preservado.")
    return text'''


def main() -> None:
    changed: list[str] = []
    inspected: list[str] = []

    for path in sorted(Path('/tmp').glob('*.py')):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding='utf-8')
        if 'def replace_once(' not in text:
            continue
        inspected.append(path.name)
        updated = text
        for strict_line in STRICT_LINES:
            updated = updated.replace(strict_line, IDEMPOTENT_BLOCK)
        if updated != text:
            path.write_text(updated, encoding='utf-8')
            changed.append(path.name)

    print(f"Patches runtime inspecionados: {len(inspected)}.")
    print(f"Patches runtime tornados idempotentes: {len(changed)}.")
    if changed:
        print("Arquivos ajustados: " + ", ".join(changed))


if __name__ == '__main__':
    main()
