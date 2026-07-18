from pathlib import Path
import re


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


# 1) Regras finais de conversa: histórico como contexto, sem reescrever relatório a cada rodada.
prompt_path = Path('/app/app/services/domnai_brain.py')
prompt = prompt_path.read_text(encoding='utf-8')
conversation_rules = '''
22. Em conversas de descoberta, planejamento ou construção de projeto, acumule internamente as informações fornecidas pelo usuário, mas responda prioritariamente apenas ao ponto mais recente. Não reescreva, recapitule ou reapresente toda a análise anterior a cada nova resposta.
23. Faça perguntas objetivas e naturais somente quando uma informação realmente necessária estiver faltando. Prefira uma pergunta por vez ou um pequeno grupo de perguntas diretamente relacionadas. Não transforme a conversa em formulário rígido.
24. Só produza consolidação extensa, plano completo, relatório ou resumo geral quando o usuário pedir claramente para resumir, consolidar, montar o plano, criar relatório ou gerar arquivo.
25. Quando uma conversa produtiva e extensa estiver sendo encerrada e já houver material suficiente para um documento útil, ofereça uma única vez a possibilidade de organizar o conteúdo em PDF. Não gere automaticamente, não insista e não faça essa oferta em despedidas casuais sem conteúdo relevante.
26. Ao gerar documento, use como título o assunto real consolidado da conversa, nunca apenas o nome genérico da operação. Trate números sugeridos, estimativas e hipóteses como premissas para teste quando não tiverem sido confirmados pelo usuário.
'''
if 'Em conversas de descoberta, planejamento ou construção de projeto' not in prompt:
    marker = '20. Nunca afirme que criou, enviou ou compartilhou e-mail, planilha, arquivo ou link externo sem confirmação técnica.\n'
    require(marker in prompt, 'Marcador das regras centrais não encontrado em domnai_brain.py.')
    prompt = prompt.replace(marker, conversation_rules + marker, 1)
prompt_path.write_text(prompt, encoding='utf-8')


# 2) Backend: sempre devolver ao frontend um texto posterior ao arquivo.
worker_path = Path('/app/app/services/chat_task_worker.py')
worker = worker_path.read_text(encoding='utf-8')
post_text = (
    'Confira o arquivo com calma. Se perceber que algum ponto ficou incompleto, incorreto ou diferente '
    'do que foi definido na conversa, me diga o trecho e eu preparo uma versão corrigida.'
)

# Troca a mensagem genérica inserida pelo patch progressivo.
worker = worker.replace(
    'Importante: Este documento tem finalidade informativa e foi elaborado com base nas informações fornecidas durante esta conversa. Para decisões definitivas, recomenda-se sempre a validação por um profissional habilitado.',
    post_text,
)

# Garante que o resultado persistido da tarefa carregue o texto posterior.
result_anchor = '            "artifacts": artifacts,\n            "provider": result.provider,\n'
if '"post_artifact_text":' not in worker:
    require(result_anchor in worker, 'Bloco do resultado da tarefa não encontrado.')
    worker = worker.replace(
        result_anchor,
        '            "artifacts": artifacts,\n'
        f'            "post_artifact_text": {post_text!r} if artifacts else "",\n'
        '            "provider": result.provider,\n',
        1,
    )
else:
    worker = re.sub(
        r'("post_artifact_text"\s*:\s*)([^,\n]+)',
        rf'\1{post_text!r} if artifacts else ""',
        worker,
        count=1,
    )

worker_path.write_text(worker, encoding='utf-8')


# 3) Frontend: ao concluir uma tarefa com arquivo, inserir uma mensagem separada depois do cartão do arquivo.
dashboard_path = Path('/frontend/src/Dashboard.jsx')
dashboard = dashboard_path.read_text(encoding='utf-8')
old_block = '''          setMessages((current) => current.map((message) => (
            message.taskId === taskId && message.role === 'assistant'
              ? {
                  ...message,
                  text: result.reply || 'O DomnAI não retornou uma resposta em texto.',
                  attachments: artifacts,
                  processing: false,
                  isError: false,
                }
              : message
          )));'''
new_block = '''          setMessages((current) => {
            const completed = current.map((message) => (
              message.taskId === taskId && message.role === 'assistant'
                ? {
                    ...message,
                    text: result.reply || 'O DomnAI não retornou uma resposta em texto.',
                    attachments: artifacts,
                    processing: false,
                    isError: false,
                  }
                : message
            ));
            const postText = String(result.post_artifact_text || '').trim();
            if (!artifacts.length || !postText) return completed;
            const postId = `assistant-${taskId}-post-artifact`;
            if (completed.some((message) => message.id === postId)) return completed;
            return [...completed, {
              id: postId,
              role: 'assistant',
              text: postText,
              attachments: [],
              processing: false,
              isError: false,
              taskId,
            }];
          });'''
if new_block not in dashboard:
    require(old_block in dashboard, 'Bloco de conclusão do polling não encontrado em Dashboard.jsx.')
    dashboard = dashboard.replace(old_block, new_block, 1)
dashboard_path.write_text(dashboard, encoding='utf-8')

print('Conversa progressiva, oferta contextual de PDF e mensagem posterior ao arquivo finalizadas.')