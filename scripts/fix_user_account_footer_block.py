from pathlib import Path
import re

DASHBOARD = Path('/frontend/src/Dashboard.jsx')
ADMIN = Path('/frontend/src/AdminAccessBoundary.jsx')
LOGOUT = Path('/frontend/src/dashboard-logout-enhancements.js')
MAIN = Path('/frontend/src/main.jsx')


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'{label}: esperado 1 trecho, encontrado {count}.')
    return source.replace(old, new, 1)


# 1. Cria um bloco nativo no rodapé do Dashboard, preservando o perfil existente.
dashboard_source = DASHBOARD.read_text(encoding='utf-8')
profile_pattern = re.compile(
    r'(?P<indent>\s*)<div className="sidebar-profile"><UserButton afterSignOutUrl="/" /><div><strong>Minha conta</strong><small>Perfil e acesso</small></div></div>'
)
profile_matches = list(profile_pattern.finditer(dashboard_source))
if len(profile_matches) != 1:
    raise SystemExit(f'Perfil lateral: esperado 1 trecho, encontrado {len(profile_matches)}.')

match = profile_matches[0]
indent = match.group('indent')
replacement = (
    f'{indent}<div className="domnai-user-account-block">\n'
    f'{indent}  <div className="domnai-user-admin-slot" data-domnai-admin-slot="true" />\n'
    f'{indent}  <div className="sidebar-profile"><UserButton afterSignOutUrl="/" /><div><strong>Minha conta</strong><small>Perfil e acesso</small></div></div>\n'
    f'{indent}  <div className="domnai-user-logout-slot" data-domnai-logout-slot="true" />\n'
    f'{indent}</div>'
)
dashboard_source = dashboard_source[:match.start()] + replacement + dashboard_source[match.end():]
DASHBOARD.write_text(dashboard_source, encoding='utf-8')


# 2. Mantém o botão Adm sob controle do React, mas passa a renderizá-lo no slot superior.
admin_source = ADMIN.read_text(encoding='utf-8')
old_entry = '''function UserAdminEntry({ onOpen }) {
  return (
    <div className="sidebar-group domnai-user-admin-group" data-domnai-admin-menu="true">
      <p>Admin</p>
      <button type="button" className="domnai-user-admin-button" onClick={onOpen}>
        <span>◇</span>
        Painel Adm
        <small>Adm</small>
      </button>
    </div>
  );
}
'''
new_entry = '''function UserAdminEntry({ onOpen }) {
  return (
    <div className="domnai-user-admin-entry" data-domnai-admin-menu="true">
      <button type="button" className="domnai-user-admin-button" onClick={onOpen}>
        Painel Adm
      </button>
    </div>
  );
}
'''
admin_source = replace_once(admin_source, old_entry, new_entry, 'Entrada administrativa do usuário')
admin_source = replace_once(
    admin_source,
    "      const navigation = document.querySelector('.sidebar-navigation');\n",
    "      const navigation = document.querySelector('[data-domnai-admin-slot=\"true\"]');\n",
    'Destino do portal administrativo',
)
ADMIN.write_text(admin_source, encoding='utf-8')


# 3. Preserva a função de logout e apenas muda seu slot e conteúdo visual.
logout_source = LOGOUT.read_text(encoding='utf-8')
old_install = '''function installSidebarLogout() {
  const sidebar = document.querySelector('.domnai-sidebar');
  const profile = sidebar?.querySelector('.sidebar-profile');
  if (!sidebar || !profile) return;

  let logoutButton = sidebar.querySelector('.domnai-sidebar-logout');
  if (!logoutButton) {
    logoutButton = document.createElement('button');
    logoutButton.type = 'button';
    logoutButton.className = 'domnai-sidebar-logout';
    logoutButton.innerHTML = '<span aria-hidden="true">↪</span><strong>Sair da conta</strong>';
    logoutButton.addEventListener('click', () => domnaiSignOut(logoutButton));
  }

  if (logoutButton.nextElementSibling !== profile) {
    sidebar.insertBefore(logoutButton, profile);
  }
}
'''
new_install = '''function installSidebarLogout() {
  const sidebar = document.querySelector('.domnai-sidebar');
  const logoutSlot = sidebar?.querySelector('[data-domnai-logout-slot="true"]');
  if (!sidebar || !logoutSlot) return;

  let logoutButton = sidebar.querySelector('.domnai-sidebar-logout');
  if (!logoutButton) {
    logoutButton = document.createElement('button');
    logoutButton.type = 'button';
    logoutButton.className = 'domnai-sidebar-logout';
    logoutButton.innerHTML = '<strong>Sair da conta</strong>';
    logoutButton.addEventListener('click', () => domnaiSignOut(logoutButton));
  }

  if (logoutButton.parentElement !== logoutSlot) {
    logoutSlot.appendChild(logoutButton);
  }
}
'''
logout_source = replace_once(logout_source, old_install, new_install, 'Instalação do logout lateral')
LOGOUT.write_text(logout_source, encoding='utf-8')


# 4. Carrega os estilos depois dos refinamentos atuais, sem sobrescrever outros módulos.
main_source = MAIN.read_text(encoding='utf-8')
old_import = "import './dashboard-sidebar-cleanup.css';\n"
new_import = "import './dashboard-sidebar-cleanup.css';\nimport './dashboard-user-account-block.css';\n"
main_source = replace_once(main_source, old_import, new_import, 'Importação do bloco da conta')
MAIN.write_text(main_source, encoding='utf-8')

print('Rodapé do usuário organizado como Painel Adm, Perfil e Sair da conta.')
