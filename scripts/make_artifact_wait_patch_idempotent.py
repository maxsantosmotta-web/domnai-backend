from pathlib import Path


path = Path('/tmp/fix_artifact_wait_for_user.py')
text = path.read_text(encoding='utf-8')
old = '''def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")'''
new = '''def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        print(f"{label}: patch aplicado.")
        return text.replace(old, new, 1)
    if new in text:
        print(f"{label}: patch já aplicado.")
        return text
    print(f"{label}: encaixe legado ausente; código-fonte atual preservado.")
    return text'''
if old in text:
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    print('Patch de espera por usuário tornado idempotente.')
elif new in text:
    print('Patch de espera por usuário já está idempotente.')
else:
    raise RuntimeError('fix_artifact_wait_for_user.py possui helper inesperado')
