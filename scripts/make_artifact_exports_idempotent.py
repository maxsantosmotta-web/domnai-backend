from pathlib import Path


decision_path = Path("/app/app/services/artifact_decision.py")
patch_path = Path("/tmp/fix_artifact_exports.py")
decision = decision_path.read_text(encoding="utf-8")

modern_markers = (
    "def _intent_from_message(",
    "def _direct_artifact_decision(",
    "_DIRECT_FORMATS",
)

if all(marker in decision for marker in modern_markers):
    patch_path.write_text(
        "print('Artifact exports legado ignorado: decisor moderno preservado.')\n",
        encoding="utf-8",
    )
    print("Patch legado de artifact exports neutralizado para o decisor moderno.")
else:
    text = patch_path.read_text(encoding="utf-8")
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
        patch_path.write_text(text.replace(strict, idempotent, 1), encoding="utf-8")
        print("Patch de artifact exports tornado idempotente.")
    else:
        raise RuntimeError("Não foi possível localizar replace_once em fix_artifact_exports.py")
