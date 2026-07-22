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

view_path = Path('/frontend/src/AdminUsersView.jsx')
view = view_path.read_text(encoding='utf-8')
state_marker = "  const [error, setError] = useState('');\n"
state_addition = "  const [deletingUserId, setDeletingUserId] = useState('');\n"
if state_addition not in view:
    if state_marker not in view:
        raise RuntimeError('Estado do módulo Usuários não localizado.')
    view = view.replace(state_marker, state_marker + state_addition, 1)

function_marker = '''  function handleExport(event) {
    event.currentTarget.blur();
    exportUsersCsv(visibleUsers);
  }
'''
function_addition = '''

  async function handleDeleteUser(item) {
    if (!item?.id || item.role === 'admin' || deletingUserId) return;
    const identity = item.email || item.name || 'este usuário';
    const confirmed = window.confirm(
      `Excluir permanentemente ${identity}? O acesso será removido e esta ação não pode ser desfeita pelo painel.`,
    );
    if (!confirmed) return;

    setDeletingUserId(item.id);
    try {
      const token = await getToken();
      if (!token) throw new Error('Não foi possível validar a sessão administrativa.');
      const response = await fetch(`/api/admin/users/${encodeURIComponent(item.id)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await readResponse(response);
      if (!response.ok) throw new Error(payload.detail || `Falha ao excluir usuário (${response.status}).`);
      setItems((current) => current.filter((user) => user.id !== item.id));
      await loadUsers({ silent: true });
    } catch (deleteError) {
      window.alert(deleteError?.message || 'Não foi possível excluir o usuário.');
    } finally {
      setDeletingUserId('');
    }
  }
'''
if 'async function handleDeleteUser(item)' not in view:
    if function_marker not in view:
        raise RuntimeError('Função de exportação do módulo Usuários não localizada.')
    view = view.replace(function_marker, function_marker + function_addition, 1)

header_marker = '                    <th>Última atividade</th>\n'
if '                    <th>Ações</th>\n' not in view:
    if header_marker not in view:
        raise RuntimeError('Cabeçalho da tabela de usuários não localizado.')
    view = view.replace(header_marker, header_marker + '                    <th>Ações</th>\n', 1)

cell_marker = '''                      <td>
                        <time dateTime={item.lastActivityAt || undefined}>
                          {formatDate(item.lastActivityAt, true)}
                        </time>
                      </td>
'''
cell_addition = '''                      <td className="user-actions-cell">
                        <button
                          type="button"
                          className="delete-user-button"
                          onClick={() => handleDeleteUser(item)}
                          disabled={item.role === 'admin' || deletingUserId === item.id}
                          title={item.role === 'admin' ? 'Contas administrativas são protegidas.' : 'Excluir usuário'}
                        >
                          {deletingUserId === item.id ? 'Excluindo...' : 'Excluir'}
                        </button>
                      </td>
'''
if 'className="delete-user-button"' not in view:
    if cell_marker not in view:
        raise RuntimeError('Coluna final da tabela de usuários não localizada.')
    view = view.replace(cell_marker, cell_marker + cell_addition, 1)
view_path.write_text(view, encoding='utf-8')

css_path = Path('/frontend/src/admin-users-view.css')
css = css_path.read_text(encoding='utf-8')
styles = r'''

.domnai-admin-users-table .user-actions-cell {
  width: 108px;
  text-align: right;
}

.domnai-admin-users-table .delete-user-button {
  border: 1px solid rgba(255, 92, 92, 0.45);
  border-radius: 8px;
  background: rgba(120, 20, 20, 0.16);
  color: #ff9a9a;
  padding: 7px 11px;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.domnai-admin-users-table .delete-user-button:hover:not(:disabled) {
  background: rgba(160, 30, 30, 0.28);
  border-color: rgba(255, 110, 110, 0.72);
}

.domnai-admin-users-table .delete-user-button:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}
'''
if '.delete-user-button' not in css:
    css = css.rstrip() + styles + '\n'
css_path.write_text(css, encoding='utf-8')

print('Catálogo final e exclusão manual de usuários conectados ao frontend.')
