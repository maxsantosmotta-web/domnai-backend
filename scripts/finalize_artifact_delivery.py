from pathlib import Path

# 1) Aceitar delegação natural do usuário como autorização para concluir o arquivo oferecido.
decision_path = Path('/app/app/services/artifact_decision.py')
decision = decision_path.read_text(encoding='utf-8')

exact_marker = '''_ACCEPTANCE_EXACT = {
    "sim",
    "pode",
    "quero",
    "ok",
    "claro",
    "perfeito",
}'''
exact_replacement = '''_ACCEPTANCE_EXACT = {
    "sim",
    "pode",
    "quero",
    "ok",
    "claro",
    "perfeito",
    "voce decide",
    "você decide",
    "pode escolher",
    "como achar melhor",
    "como voce achar melhor",
    "como você achar melhor",
}'''
if exact_marker in decision:
    decision = decision.replace(exact_marker, exact_replacement, 1)
elif '"como você achar melhor"' not in decision:
    raise RuntimeError('Bloco de aceites do decisor de artefatos não encontrado.')

phrase_marker = '''    "gere a planilha",
    "crie a planilha",
)'''
phrase_replacement = '''    "gere a planilha",
    "crie a planilha",
    "voce decide",
    "você decide",
    "pode escolher",
    "escolha voce",
    "escolha você",
    "como achar melhor",
    "como voce achar melhor",
    "como você achar melhor",
    "da forma que achar melhor",
    "do jeito que achar melhor",
)'''
if phrase_marker in decision:
    decision = decision.replace(phrase_marker, phrase_replacement, 1)
elif '"do jeito que achar melhor"' not in decision:
    raise RuntimeError('Bloco de frases de aceite do decisor não encontrado.')

decision_path.write_text(decision, encoding='utf-8')

# 2) Finalizar a entrega somente depois da criação real e remover contradições.
worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')

helper_marker = '''def _elapsed_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))
'''
helper = '''def _elapsed_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))


def _clean_artifact_contradictions(text: str) -> str:
    paragraphs = [part.strip() for part in str(text or "").split("\\n\\n") if part.strip()]
    blocked = (
        "nao consigo enviar arquivos",
        "não consigo enviar arquivos",
        "nao posso enviar arquivos",
        "não posso enviar arquivos",
        "nao consigo anexar arquivos",
        "não consigo anexar arquivos",
        "nao posso anexar arquivos",
        "não posso anexar arquivos",
        "nao consigo gerar arquivos",
        "não consigo gerar arquivos",
    )
    kept = [part for part in paragraphs if not any(marker in part.casefold() for marker in blocked)]
    return "\\n\\n".join(kept).strip()


def _artifact_completion_message(artifact_type: str | None) -> str:
    if artifact_type in {"xlsx", "csv"}:
        return (
            "Pronto! Sua planilha foi gerada com base nas informações da conversa e está disponível logo abaixo. "
            "Ela também foi salva automaticamente na Biblioteca para você abrir novamente quando precisar."
        )
    return (
        "Pronto! Seu PDF foi gerado com base nas informações da conversa e está disponível logo abaixo. "
        "Ele também foi salvo automaticamente na Biblioteca para você abrir novamente quando precisar."
    )
'''
if '_clean_artifact_contradictions' not in worker:
    if helper_marker not in worker:
        raise RuntimeError('Ponto de inserção da finalização de artefatos não encontrado.')
    worker = worker.replace(helper_marker, helper, 1)

old_success = '''                artifacts.append(artifact)
                if result.provider == "local-artifact":
                    reply = "PDF criado e enviado aqui no chat. O mesmo arquivo também foi salvo automaticamente na Biblioteca."
                else:
                    reply = f"{reply.rstrip()}\\n\\nArquivo criado e enviado aqui no chat."'''
new_success = '''                artifacts.append(artifact)
                clean_reply = _clean_artifact_contradictions(reply)
                completion = _artifact_completion_message(decision.get("artifact_type"))
                reply = f"{clean_reply}\\n\\n{completion}" if clean_reply else completion'''
if old_success in worker:
    worker = worker.replace(old_success, new_success, 1)
elif '_artifact_completion_message(decision.get("artifact_type"))' not in worker:
    raise RuntimeError('Bloco de sucesso da geração de arquivo não encontrado.')

worker_path.write_text(worker, encoding='utf-8')

# 3) Impedir que o modelo encerre após prometer uma entrega ainda não concluída.
prompt_path = Path('/app/app/services/domnai_brain.py')
prompt = prompt_path.read_text(encoding='utf-8')
anchor = '20. Nunca afirme que criou, enviou ou compartilhou e-mail, planilha, arquivo ou link externo sem confirmação técnica.\n'
rule = (
    '20. Se o usuário aceitar ou delegar a criação de PDF, planilha ou arquivo com frases como "pode", '
    '"você decide" ou "como achar melhor", trate isso como autorização para concluir a entrega agora. '
    'Não faça nova pergunta sobre formato quando o melhor formato puder ser inferido. Não encerre o atendimento, '
    'não se despeça e não diga que ficará à disposição antes de o arquivo ser realmente criado e apresentado.\n'
)
if 'Não encerre o atendimento, não se despeça' not in prompt:
    if anchor not in prompt:
        raise RuntimeError('Regra de confirmação técnica não encontrada no prompt central.')
    prompt = prompt.replace(anchor, rule + anchor, 1)
prompt_path.write_text(prompt, encoding='utf-8')
