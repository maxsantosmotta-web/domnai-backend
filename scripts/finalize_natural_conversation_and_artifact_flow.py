from pathlib import Path
import re


POST_ARTIFACT_TEXT = (
    "Este documento foi gerado com base nas informações fornecidas durante esta conversa. "
    "Seu conteúdo tem finalidade informativa e não substitui a análise, avaliação ou orientação "
    "de um profissional habilitado quando ela for necessária."
)


def replace_once(text: str, old: str, new: str) -> tuple[str, bool]:
    if new in text:
        return text, True
    if old not in text:
        return text, False
    return text.replace(old, new, 1), True


applied = []


# =========================
# BACKEND / RUNTIME
# =========================
prompt_path = Path('/app/app/services/domnai_brain.py')
worker_path = Path('/app/app/services/chat_task_worker.py')
orchestrator_path = Path('/app/app/services/orchestrated_brain.py')
artifact_decision_path = Path('/app/app/services/artifact_decision.py')
chat_api_path = Path('/app/app/api/chat.py')

if prompt_path.exists():
    prompt = prompt_path.read_text(encoding='utf-8')
    rules = '''

MODO DE CONVERSA PROGRESSIVA
- Durante descoberta, planejamento ou construção de projeto, use todo o histórico como contexto, mas responda prioritariamente ao ponto mais recente.
- Não reescreva a análise inteira, não recapitule todas as decisões e não reapresente um relatório a cada nova mensagem.
- Reconheça naturalmente o que o usuário acabou de informar, avance a conversa e faça apenas a pergunta realmente necessária para o próximo passo.
- Não repita perguntas já respondidas. Quando uma correção do usuário substituir uma informação anterior, considere a correção como válida e descarte a versão antiga.
- Ajuste a profundidade à mensagem atual: respostas simples devem ser curtas; decisões complexas podem ser aprofundadas.
- Não transforme a operação ativa em formulário. A operação fornece especialidade, mas a última mensagem define o que deve ser respondido agora.

MODO DE CONSOLIDAÇÃO
- Só faça resumo geral, plano completo, relatório, parecer ou documento consolidado quando o usuário pedir claramente ou aceitar uma oferta de arquivo.
- Na consolidação, diferencie fatos confirmados, decisões, estimativas, hipóteses, riscos e pontos ainda pendentes.
- Use título específico baseado no assunto real da conversa. Nunca use apenas “Documento DomnAI” quando houver contexto suficiente.

ENCERRAMENTO E ARQUIVOS
- Em despedida casual, encerre naturalmente.
- Quando houver uma conversa produtiva com informações suficientes e o usuário indicar que deseja parar, ofereça uma única vez organizar o conteúdo em PDF. Não gere automaticamente e não insista.
- Não ofereça arquivo apenas porque a última resposta ficou longa. Considere a riqueza do histórico e a utilidade real do documento.
'''
    if 'MODO DE CONVERSA PROGRESSIVA' not in prompt:
        marker = '\nPROTOCOLO DE CONFIABILIDADE\n'
        if marker in prompt:
            prompt = prompt.replace(marker, rules + marker, 1)
        else:
            prompt = prompt.rstrip() + rules + '\n'
    prompt_path.write_text(prompt, encoding='utf-8')
    applied.append('prompt conversacional')


if orchestrator_path.exists():
    source = orchestrator_path.read_text(encoding='utf-8')
    source = source.replace(
        '    if normalized in farewell_messages:\n        return "Até mais!"\n',
        '    if normalized in farewell_messages and len(history) < 4:\n        return "Até mais!"\n',
    )
    orchestrator_path.write_text(source, encoding='utf-8')
    applied.append('encerramento contextual')


if artifact_decision_path.exists():
    source = artifact_decision_path.read_text(encoding='utf-8')

    old_gate = '''    if explicit_request or accepted_previous_offer:
        return True
    if offer_already_made:
        return False
    return bool(operation and len(str(answer or "").strip()) >= 1000)
'''
    new_gate = '''    if explicit_request or accepted_previous_offer:
        return True
    if offer_already_made:
        return False

    relevant_turns = sum(
        1
        for item in history[-24:]
        if str(item.get("role") or "").strip().lower() in {"user", "assistant"}
        and len(str(item.get("content") or "").strip()) >= 40
    )
    closing_markers = (
        "vamos parar por aqui", "vamos parar por hoje", "paramos por aqui",
        "podemos parar", "depois continuamos", "continuamos depois",
        "por hoje chega", "encerrar por hoje",
    )
    closing_signal = any(marker in normalized for marker in closing_markers)
    rich_conversation = relevant_turns >= 8 or len(_history_text(history, limit=20)) >= 2200
    return bool(operation and closing_signal and rich_conversation)
'''
    source, _ = replace_once(source, old_gate, new_gate)

    source = source.replace(
        '- Use offer somente quando um arquivo agregaria valor relevante, a explicação estiver concluída e não existir oferta anterior no histórico.\n',
        '- Use offer somente quando um arquivo agregar valor real, houver contexto suficiente acumulado e não existir oferta anterior no histórico. Não ofereça apenas porque a última resposta é longa.\n',
    )
    source = source.replace(
        '- Uma oferta de arquivo pode acontecer no máximo uma vez por conversa.\n',
        '- Uma oferta de arquivo pode acontecer no máximo uma vez por conversa. Em sinal de encerramento após conversa rica, prefira offer; em despedida casual, use none.\n',
    )
    artifact_decision_path.write_text(source, encoding='utf-8')
    applied.append('gatilho contextual de arquivo')


if chat_api_path.exists():
    source = chat_api_path.read_text(encoding='utf-8')
    source = source.replace(
        '    title = str(decision.get("title") or "Documento DomnAI").strip()[:180]\n',
        '    title = str(decision.get("title") or operation or "Relatório consolidado").strip()[:180]\n'
        '    if title.casefold() == "documento domnai" and operation:\n'
        '        title = str(operation).strip()[:180]\n',
    )
    source = source.replace(
        '                "summary": answer,\n                "sections": [{"title": "Resultado", "content": answer}],\n',
        '                "summary": "",\n                "sections": [{"title": "Conteúdo consolidado", "content": answer}],\n',
    )
    if '"postArtifactText": POST_ARTIFACT_TEXT if artifact else ""' not in source:
        if 'POST_ARTIFACT_TEXT =' not in source:
            insert_at = source.find('\n\nrouter = APIRouter')
            if insert_at >= 0:
                source = source[:insert_at] + f'\n\nPOST_ARTIFACT_TEXT = {POST_ARTIFACT_TEXT!r}\n' + source[insert_at:]
        source = source.replace(
            '        "artifact": artifact,\n        "provider": result.provider,\n',
            '        "artifact": artifact,\n'
            '        "postArtifactText": POST_ARTIFACT_TEXT if artifact else "",\n'
            '        "provider": result.provider,\n',
            1,
        )
    chat_api_path.write_text(source, encoding='utf-8')
    applied.append('título e PDF sem duplicação')


if worker_path.exists():
    source = worker_path.read_text(encoding='utf-8')

    # Substitui qualquer uma das mensagens posteriores já usadas.
    variants = [
        'Importante: Este documento tem finalidade informativa e foi elaborado com base nas informações fornecidas durante esta conversa. Para decisões definitivas, recomenda-se sempre a validação por um profissional habilitado.',
        'Confira o arquivo com calma. Se perceber que algum ponto ficou incompleto, incorreto ou diferente do que foi definido na conversa, me diga o trecho e eu preparo uma versão corrigida.',
    ]
    for variant in variants:
        source = source.replace(variant, POST_ARTIFACT_TEXT)

    # Título contextual antes da criação.
    decision_anchor = '''        decision = decide_artifact(
            message=original_message,
            operation=operation,
            history=history,
            answer=reply,
        )
'''
    decision_block = decision_anchor + '''        if str(decision.get("title") or "").strip().casefold() in {"", "documento domnai"}:
            decision["title"] = str(operation or "Relatório consolidado").strip()
'''
    source, _ = replace_once(source, decision_anchor, decision_block)

    # Resultado da tarefa precisa transportar a mensagem posterior ao frontend.
    result_anchor = '            "artifacts": artifacts,\n            "provider": result.provider,\n'
    if '"post_artifact_text":' not in source and result_anchor in source:
        source = source.replace(
            result_anchor,
            '            "artifacts": artifacts,\n'
            f'            "post_artifact_text": {POST_ARTIFACT_TEXT!r} if artifacts else "",\n'
            '            "provider": result.provider,\n',
            1,
        )
    else:
        source = re.sub(
            r'("post_artifact_text"\s*:\s*)([^,\n]+)',
            lambda match: match.group(1) + repr(POST_ARTIFACT_TEXT) + ' if artifacts else ""',
            source,
            count=1,
        )

    worker_path.write_text(source, encoding='utf-8')
    applied.append('entrega e texto posterior')


# =========================
# FRONTEND / BUILD
# =========================
dashboard_path = Path('/frontend/src/Dashboard.jsx')
if dashboard_path.exists():
    source = dashboard_path.read_text(encoding='utf-8')

    if 'result.post_artifact_text' not in source:
        pattern = re.compile(
            r'(?P<indent>[ \t]*)setMessages\(\(current\) => current\.map\(\(message\) => \(\s*'
            r'message\.taskId === taskId && message\.role === [\'\"]assistant[\'\"]\s*'
            r'\? \{.*?text: result\.reply \|\| [\'\"]O DomnAI não retornou uma resposta em texto\.[\'\"],.*?'
            r': message\s*\)\)\);',
            re.DOTALL,
        )
        match = pattern.search(source)
        if match:
            indent = match.group('indent')
            replacement = f'''{indent}setMessages((current) => {{
{indent}  const completed = current.map((message) => (
{indent}    message.taskId === taskId && message.role === 'assistant'
{indent}      ? {{
{indent}          ...message,
{indent}          text: result.reply || 'O DomnAI não retornou uma resposta em texto.',
{indent}          attachments: artifacts,
{indent}          processing: false,
{indent}          isError: false,
{indent}        }}
{indent}      : message
{indent}  ));
{indent}  const postText = String(result.post_artifact_text || result.postArtifactText || '').trim();
{indent}  if (!artifacts.length || !postText) return completed;
{indent}  const postId = `assistant-${{taskId}}-post-artifact`;
{indent}  if (completed.some((message) => message.id === postId)) return completed;
{indent}  return [...completed, {{
{indent}    id: postId,
{indent}    role: 'assistant',
{indent}    text: postText,
{indent}    attachments: [],
{indent}    processing: false,
{indent}    isError: false,
{indent}    taskId,
{indent}  }}];
{indent}}});'''
            source = source[:match.start()] + replacement + source[match.end():]
        else:
            raise RuntimeError('Fluxo de conclusão da tarefa não localizado no Dashboard.jsx.')

    dashboard_path.write_text(source, encoding='utf-8')
    applied.append('mensagem posterior no frontend')


if not applied:
    raise RuntimeError('Nenhum arquivo conhecido do chat foi encontrado nesta etapa do build.')

print('Camada final do chat aplicada: ' + ', '.join(applied))
