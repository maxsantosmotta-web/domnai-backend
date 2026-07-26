from pathlib import Path
import re


CHAT_PATH = Path('/app/app/api/chat.py')


def main() -> None:
    source = CHAT_PATH.read_text(encoding='utf-8')

    source = source.replace(
        'from app.services.credit_meter import charge_artifact, charge_usage, ensure_artifact_credit, ensure_minimum_credit',
        'from app.services.credit_meter import charge_usage, ensure_minimum_credit',
        1,
    )

    source, ensure_count = re.subn(
        r'^\s*ensure_artifact_credit\(user_id, artifact_type\)\s*\n',
        '',
        source,
        count=1,
        flags=re.M,
    )
    if ensure_count not in {0, 1}:
        raise RuntimeError(f'Remoção da validação antiga de artefato inválida: {ensure_count}')

    charge_pattern = re.compile(
        r'\n\s*artifact_usage = charge_artifact\(\n'
        r'\s*user_id,\n'
        r'\s*artifact_type,\n'
        r'\s*idempotency_key=billing_key,\n'
        r'\s*\)\n',
        re.M,
    )
    source, charge_count = charge_pattern.subn(
        '\n    artifact_usage = {"charged_credits": 0, "remaining_credits": None, "includedInOperation": True}\n',
        source,
        count=1,
    )
    if charge_count not in {0, 1}:
        raise RuntimeError(f'Remoção da cobrança antiga de artefato inválida: {charge_count}')

    source = source.replace(
        'f"{artifact_usage.get(\'charged_credits\', 0)} crédito(s) consumido(s)."',
        '"Arquivo incluído na operação, sem débito adicional."',
        1,
    )

    checks = {
        'cobrança de artefato removida': source.count('charge_artifact('),
        'validação financeira de artefato removida': source.count('ensure_artifact_credit('),
        'marcação sem débito': source.count('"includedInOperation": True'),
        'auditoria sem débito': source.count('Arquivo incluído na operação, sem débito adicional.'),
        'entrega preservada': source.count('"savedToLibrary": True'),
    }
    if checks['cobrança de artefato removida'] != 0:
        raise RuntimeError(f'Cobrança adicional de arquivo ainda presente: {checks}')
    if checks['validação financeira de artefato removida'] != 0:
        raise RuntimeError(f'Validação antiga de arquivo ainda presente: {checks}')
    if checks['marcação sem débito'] != 1 or checks['auditoria sem débito'] != 1:
        raise RuntimeError(f'Contrato de arquivo incluído na operação inválido: {checks}')
    if checks['entrega preservada'] != 1:
        raise RuntimeError(f'Persistência do arquivo foi alterada: {checks}')

    compile(source, str(CHAT_PATH), 'exec')
    CHAT_PATH.write_text(source, encoding='utf-8')
    print('Arquivos incluídos na operação sem cobrança adicional; entrega e Biblioteca preservadas.')


if __name__ == '__main__':
    main()
