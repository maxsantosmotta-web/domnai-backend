from pathlib import Path

path = Path('/app/app/services/domnai_brain.py')
source = path.read_text(encoding='utf-8')

marker = '17. Seja objetivo, mas aprofunde quando a decisão exigir.'
replacement = '''17. Seja objetivo, mas aprofunde quando a decisão exigir.
18. Para pedidos simples, responda em até 6 parágrafos curtos. Não repita contexto, conclusão ou oferta de ajuda.
19. Encerre assim que o pedido estiver resolvido. Não prolongue a conversa com sugestões em cadeia.
20. Nunca afirme que criou, enviou ou compartilhou e-mail, planilha, arquivo ou link externo sem confirmação técnica.
21. Nunca invente URL. Só apresente links recebidos de ferramenta ou integração real.
22. Não prometa retornar depois ou concluir algo em instantes. Entregue o que for possível na resposta atual.'''
if marker not in source:
    raise RuntimeError('Regras centrais não encontradas.')
source = source.replace(marker, replacement, 1)
source = source.replace('def _normalized_history(history: list[dict], limit: int = 16)', 'def _normalized_history(history: list[dict], limit: int = 10)', 1)
source = source.replace('content[:12000]', 'content[:6000]')
source = source.replace('"max_tokens": 1800', '"max_tokens": 1200')
path.write_text(source, encoding='utf-8')
