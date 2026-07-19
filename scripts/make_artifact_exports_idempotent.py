from pathlib import Path


path = Path("/tmp/fix_artifact_exports.py")
text = path.read_text(encoding="utf-8")

strict = '''def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")'''

idempotent = '''def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        print(f"{label}: patch aplicado.")
        return text.replace(old, new, 1)
    if new in text:
        print(f"{label}: patch já estava aplicado.")
        return text
    print(f"{label}: encaixe legado ausente; código-fonte atual preservado.")
    return text'''

if idempotent in text:
    print("Patch de artifact exports já está idempotente.")
elif strict in text:
    path.write_text(text.replace(strict, idempotent, 1), encoding="utf-8")
    print("Patch de artifact exports tornado idempotente.")
else:
    raise RuntimeError("Não foi possível localizar replace_once em fix_artifact_exports.py")
