from pathlib import Path

path = Path('/frontend/src/dashboard-billing-enhancements.js')
source = path.read_text(encoding='utf-8')

old = '''      <button type="button" class="billing-back-to-chat" data-billing-action="back-to-chat" aria-label="Voltar ao chat"><span>←</span><span class="billing-back-label">Voltar ao chat</span></button>'''
new = '''      <button type="button" class="billing-back-to-chat${noPlan ? ' billing-approved-back' : ''}" data-billing-action="back-to-chat" ${noPlan ? 'data-approved-billing-back="true"' : ''} aria-label="${noPlan ? 'Sair da conta' : 'Voltar ao chat'}">${noPlan ? 'Sair da conta' : '<span>←</span><span class="billing-back-label">Voltar ao chat</span>'}</button>'''

if old not in source:
    raise RuntimeError('Não foi possível localizar o botão inicial do Faturamento.')

path.write_text(source.replace(old, new, 1), encoding='utf-8')
