from pathlib import Path

view_path = Path('/frontend/src/AdminUsersView.jsx')
source = view_path.read_text(encoding='utf-8')

state_marker = "  const [error, setError] = useState('');\n"
state_addition = "  const [deletingUserId, setDeletingUserId] = useState('');\n"
if state_addition not in source:
    if state_marker not in source:
        raise RuntimeError('Estado de erro do módulo Usuários não localizado.')
    source = source.replace(state_marker, state_marker + state_addition, 1)

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
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Não foi possível validar a sessão administrativa.');
      const response = await fetch(`/api/admin/users/${encodeURIComponent(item.id)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await readResponse(response);
      if (!response.ok) {
        throw new Error(payload.detail || `Falha ao excluir usuário (${response.status}).`);
      }
      setItems((current) => current.filter((user) => user.id !== item.id));
      await loadUsers({ silent: true });
    } catch (deleteError) {
      window.alert(deleteError?.message || 'Não foi possível excluir o usuário.');
    } finally {
      setDeletingUserId('');
    }
  }
'''
if 'async function handleDeleteUser(item)' not in source:
    if function_marker not in source:
        raise RuntimeError('Função de exportação do módulo Usuários não localizada.')
    source = source.replace(function_marker, function_marker + function_addition, 1)

header_marker = '                    <th>Última atividade</th>\n'
if '                    <th>Ações</th>\n' not in source:
    if header_marker not in source:
        raise RuntimeError('Cabeçalho da tabela de usuários não localizado.')
    source = source.replace(header_marker, header_marker + '                    <th>Ações</th>\n', 1)

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
if 'className="delete-user-button"' not in source:
    if cell_marker not in source:
        raise RuntimeError('Última coluna da tabela de usuários não localizada.')
    source = source.replace(cell_marker, cell_marker + cell_addition, 1)

view_path.write_text(source, encoding='utf-8')

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

print('Botão de exclusão manual conectado à tabela de usuários com proteção para administradores.')
