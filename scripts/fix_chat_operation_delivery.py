from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

ref_marker = "  const operationComposerRef = useRef(null);\n"
ref_addition = "  const operationSendGuardRef = useRef(0);\n"
if ref_addition not in source:
    if source.count(ref_marker) != 1:
        raise SystemExit(f'Referência do compositor: esperado 1 trecho, encontrado {source.count(ref_marker)}.')
    source = source.replace(ref_marker, ref_marker + ref_addition, 1)

select_marker = "  function selectOperation(item) {\n    if (responding) return;\n"
select_replacement = "  function selectOperation(item) {\n    if (responding) return;\n\n    operationSendGuardRef.current = Date.now() + 900;\n"
if 'operationSendGuardRef.current = Date.now() + 900;' not in source:
    if source.count(select_marker) != 1:
        raise SystemExit(f'Seleção de operação: esperado 1 trecho, encontrado {source.count(select_marker)}.')
    source = source.replace(select_marker, select_replacement, 1)

send_marker = "  async function sendMessage(event) {\n    event.preventDefault();\n"
send_replacement = "  async function sendMessage(event) {\n    event.preventDefault();\n    if (Date.now() < operationSendGuardRef.current) return;\n"
if 'Date.now() < operationSendGuardRef.current' not in source:
    if source.count(send_marker) != 1:
        raise SystemExit(f'Envio do chat: esperado 1 trecho, encontrado {source.count(send_marker)}.')
    source = source.replace(send_marker, send_replacement, 1)

old_error = "        text: error.message || 'Não foi possível concluir a análise. Tente novamente.',"
new_error = "        text: error?.message === 'Failed to fetch' || error instanceof TypeError\n          ? 'A conexão com o DomnAI foi interrompida antes da resposta. Tente enviar novamente.'\n          : error.message || 'Não foi possível concluir a análise. Tente novamente.',"
if new_error not in source:
    if source.count(old_error) != 1:
        raise SystemExit(f'Mensagem de falha: esperado 1 trecho, encontrado {source.count(old_error)}.')
    source = source.replace(old_error, new_error, 1)

path.write_text(source, encoding='utf-8')
print('Seleção de operação protegida e falha de conexão esclarecida.')
