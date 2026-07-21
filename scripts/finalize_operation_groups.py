from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

css_import = "import './operation-groups.css';"
if css_import not in source:
    marker = "import './dashboard-adjustments.css';"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar a importação de estilos do Dashboard.')
    source = source.replace(marker, marker + "\n" + css_import, 1)

operation_groups = '''const operationGroups = [
  {
    name: 'Negócios e Finanças',
    ids: [
      'validacao-ideia', 'abrir-negocio', 'estrutura-negocio', 'diagnostico-negocio',
      'plano-acao', 'viabilidade', 'mercado-concorrencia', 'gestao-financeira',
      'precificacao', 'metas', 'compras', 'fornecedores', 'negociacao', 'dividas',
      'investimentos', 'contrato',
    ],
  },
  {
    name: 'Compras e Patrimônio',
    ids: ['veiculos', 'imoveis', 'compras-alto-valor', 'viagens-orcamento'],
  },
  {
    name: 'Carreira e Desenvolvimento',
    ids: ['carreiras', 'estudos-qualificacao', 'financas-pessoais'],
  },
  {
    name: 'Saúde, Fitness e Esportes',
    ids: [
      'treinos-academia', 'exercicios-casa', 'alimentacao-fitness', 'estatistica-apostas',
      'pilates-casa', 'yoga-casa', 'cronograma-capilar', 'cuidados-pele',
      'treino-esportivo', 'preparacao-corrida', 'alongamento-mobilidade', 'preparacao-fisica',
    ],
  },
];

'''

if 'const operationGroups = [' not in source:
    marker = 'function formatFileSize(size = 0) {'
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o fim do catálogo de operações.')
    source = source.replace(marker, operation_groups + marker, 1)

render = '''<div className="operation-groups">
            {operationGroups.map((group, groupIndex) => {
              const groupOperations = group.ids
                .map((id) => operations.find((item) => item.id === id))
                .filter(Boolean);
              return (
                <details className="operation-group" key={group.name} open={groupIndex === 0}>
                  <summary>
                    <span>{group.name}</span>
                    <span className="operation-group-count">{groupOperations.length}</span>
                  </summary>
                  <div className="operation-group-items">
                    {groupOperations.map((item) => (
                      <button
                        className={activeOperation === item.id && section === 'chat' ? 'is-active' : ''}
                        type="button"
                        key={item.id}
                        onClick={() => selectOperation(item)}
                      >
                        <span>›</span> {item.name}
                      </button>
                    ))}
                  </div>
                </details>
              );
            })}
          </div>'''

patterns = [
    r"\{operations\.map\(\(item\) => <button className=\{activeOperation === item\.id && section === 'chat' \? 'is-active' : ''\} type=\"button\" key=\{item\.id\} onClick=\{\(\) => selectOperation\(item\)\}><span>›</span> \{item\.name\}</button>\)\}",
    r"\{operations\.map\(\(item\) => <button className=\{activeOperation === item\.id \? 'active' : ''\} key=\{item\.id\} type=\"button\" onClick=\{\(\) => selectOperation\(item\)\}>\{item\.name\}</button>\)\}",
]

if 'className="operation-groups"' not in source:
    replaced = 0
    for pattern in patterns:
        source, count = re.subn(pattern, render, source, count=1)
        replaced += count
        if count:
            break
    if replaced != 1:
        raise RuntimeError('Não foi possível localizar a lista simples de operações para restaurar os blocos.')

if "id: 'rescisao'" in source or 'Cálculo de Rescisão Trabalhista' in source:
    raise RuntimeError('A operação trabalhista reapareceu no catálogo final.')

required_labels = (
    'Viabilidade Financeira e Operacional',
    'Diagnosticar Problemas do Negócio',
    'Criar Plano de Ação',
    'Definir Metas do Negócio',
    'Comparar Preços e Comprar',
    'Avaliar Fornecedores',
)
for label in required_labels:
    if label not in source:
        raise RuntimeError(f'Nome aprovado ausente no catálogo final: {label}')

path.write_text(source, encoding='utf-8')
print('Blocos de operações restaurados por categoria no frontend final.')
