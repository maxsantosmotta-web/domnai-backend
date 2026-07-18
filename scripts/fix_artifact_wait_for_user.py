from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise RuntimeError(f"{label}: trecho esperado não encontrado")


# Ajuste restrito ao gatilho automático: 1.200 caracteres apenas autorizam a
# avaliação. Se a resposta ainda pedir uma escolha ao usuário, nenhum arquivo é
# criado até a próxima mensagem.
path = Path('/app/app/services/artifact_decision.py')
text = path.read_text(encoding='utf-8')

text = text.replace(
    'os.getenv("DOMNAI_AUTO_ARTIFACT_MIN_CHARS", "800")',
    'os.getenv("DOMNAI_AUTO_ARTIFACT_MIN_CHARS", "1200")',
)

text = replace_once(
    text,
    '- Quando `automatic_generation=true`, escolha o formato pela natureza principal da entrega e retorne `action=create`; nunca devolva `offer`.',
    '- Quando `automatic_generation=true`, o limite apenas autoriza a avaliação. Se a resposta atual ainda fizer uma pergunta, apresentar alternativas ou depender de uma escolha do usuário, retorne `action=none` e aguarde a próxima mensagem. Só retorne `action=create` quando o conteúdo estiver realmente concluído e não houver decisão pendente do usuário.',
    'artifact_decision pending-user-choice rule',
)

text = replace_once(
    text,
    '''        if automatic_generation:
            chosen_type = parsed.get("artifact_type")
            if chosen_type in {"xlsx", "csv"} and not _spreadsheet_payload_is_useful(parsed):
                chosen_type = "pdf"
            if chosen_type not in {"pdf", "xlsx", "csv"}:
                chosen_type = "pdf"
            parsed["action"] = "create"
            parsed["artifact_type"] = chosen_type
''',
    '''        if automatic_generation and parsed.get("action") == "create":
            chosen_type = parsed.get("artifact_type")
            if chosen_type in {"xlsx", "csv"} and not _spreadsheet_payload_is_useful(parsed):
                chosen_type = "pdf"
            if chosen_type not in {"pdf", "xlsx", "csv"}:
                chosen_type = "pdf"
            parsed["artifact_type"] = chosen_type
        elif automatic_generation:
            parsed = dict(_NONE)
''',
    'artifact_decision do-not-force-create',
)

path.write_text(text, encoding='utf-8')
