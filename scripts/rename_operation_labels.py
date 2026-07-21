from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

replacements = {
    "{ id: 'viabilidade', name: 'Análise de Viabilidade' }": "{ id: 'viabilidade', name: 'Viabilidade Financeira e Operacional' }",
    "{ id: 'diagnostico-negocio', name: 'Diagnóstico do Negócio' }": "{ id: 'diagnostico-negocio', name: 'Diagnosticar Problemas do Negócio' }",
    "{ id: 'plano-acao', name: 'Plano de Ação Empresarial' }": "{ id: 'plano-acao', name: 'Criar Plano de Ação' }",
    "{ id: 'metas', name: 'Planejamento de Metas' }": "{ id: 'metas', name: 'Definir Metas do Negócio' }",
    "{ id: 'compras', name: 'Cotações e Compras Empresariais' }": "{ id: 'compras', name: 'Comparar Preços e Comprar' }",
    "{ id: 'fornecedores', name: 'Escolha de Fornecedores' }": "{ id: 'fornecedores', name: 'Avaliar Fornecedores' }",
}

for old, new in replacements.items():
    if old in source:
        source = source.replace(old, new, 1)
    elif new not in source:
        raise RuntimeError(f'Operação não encontrada para renomear: {old}')

# Estes dois nomes foram explicitamente mantidos pelo usuário.
for preserved in (
    "{ id: 'validacao-ideia', name: 'Validação de Ideias e Oportunidades' }",
    "{ id: 'estrutura-negocio', name: 'Estruturação e Organização Empresarial' }",
):
    if preserved not in source:
        raise RuntimeError(f'Nome que deveria ser preservado foi alterado: {preserved}')

path.write_text(source, encoding='utf-8')
print('Rótulos aprovados renomeados; nomes marcados como mantém foram preservados.')
