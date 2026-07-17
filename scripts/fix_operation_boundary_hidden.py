from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

# O marcador de operação continua existindo apenas como limite interno de contexto,
# mas não deve aparecer visualmente no chat. A operação selecionada já é exibida
# uma única vez como mensagem do usuário e é enviada automaticamente ao DomnAI.
pattern = re.compile(
    r"\{visibleMessages\.map\(\(message\) => message\.role === 'operation' \? \(\n"
    r"\s*<div className=\"chat-operation-divider\".*?</div>\n"
    r"\s*\) : \(\n",
    re.S,
)
replacement = "{visibleMessages.map((message) => message.role === 'operation' ? null : (\n"
source, count = pattern.subn(replacement, source, count=1)

if count != 1:
    # Compatibilidade com pequenas variações de formatação do JSX final.
    source, count = re.subn(
        r"message\.role === 'operation' \? \(\s*<div className=\"chat-operation-divider\".*?</div>\s*\) : \(",
        "message.role === 'operation' ? null : (",
        source,
        count=1,
        flags=re.S,
    )

if count != 1:
    raise RuntimeError('Não foi possível ocultar com segurança o marcador interno de nova operação.')

path.write_text(source, encoding='utf-8')
print('Marcador interno de operação ocultado; a operação aparece apenas uma vez no chat.')
