from pathlib import Path
import re

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

catalog_import = "import { operations, operationGroups, operationGroupInitiallyOpen, persistOperationGroup } from './operation-catalog.js';"
if catalog_import not in source:
    marker = "import './operation-groups.css';"
    if marker not in source:
        marker = "import './dashboard-adjustments.css';"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar as importações finais do Dashboard.')
    source = source.replace(marker, marker + '\n' + catalog_import, 1)

source, operations_count = re.subn(
    r"\nconst operations = \[.*?\n\];\n",
    '\n',
    source,
    count=1,
    flags=re.S,
)
if operations_count != 1:
    raise RuntimeError('Não foi possível remover o catálogo antigo do Dashboard.')

source, groups_count = re.subn(
    r"\nconst operationGroups = \[.*?\n\];\n",
    '\n',
    source,
    count=1,
    flags=re.S,
)
if groups_count != 1:
    raise RuntimeError('Não foi possível remover os blocos antigos do Dashboard.')

old_details = '<details className="operation-group" key={group.name} open={groupIndex === 0}>'
new_details = '<details className="operation-group" key={group.name} open={operationGroupInitiallyOpen(group.name, groupIndex)} onToggle={(event) => persistOperationGroup(group.name, event.currentTarget.open)}>'
if old_details in source:
    source = source.replace(old_details, new_details, 1)
elif new_details not in source:
    source, count = re.subn(
        r'<details className="operation-group" key=\{group\.name\} open=\{[^}]+\}>',
        new_details,
        source,
        count=1,
    )
    if count != 1:
        raise RuntimeError('Não foi possível ativar a persistência dos blocos.')

for forbidden in ('Análise Estatística Esportiva para Apostas', 'Cálculo de Rescisão Trabalhista'):
    if forbidden in source:
        raise RuntimeError(f'Operação removida reapareceu no Dashboard final: {forbidden}')

path.write_text(source, encoding='utf-8')
print('Catálogo final conectado ao Dashboard: 100 operações em 5 blocos persistentes.')
