from pathlib import Path
import re

ADMIN = Path('/frontend/src/AdminAccessBoundary.jsx')
DASHBOARD = Path('/frontend/src/Dashboard.jsx')


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'{label}: esperado 1 trecho, encontrado {count}.')
    return source.replace(old, new, 1)


admin_source = ADMIN.read_text(encoding='utf-8')

admin_source = replace_once(
    admin_source,
    "import './admin-menu-header-fixes.css';\n",
    "import './admin-menu-header-fixes.css';\nimport './admin-navigation-final.css';\n",
    'Importação dos estilos finais de navegação',
)

admin_source = replace_once(
    admin_source,
    '          <button type="button" className="domnai-admin-brand-back" onClick={onUser}>Voltar</button>\n',
    '',
    'Remoção do Voltar ao lado do logo',
)

admin_source = replace_once(
    admin_source,
    "                <span>{String(index + 1).padStart(2, '0')}</span>\n",
    '',
    'Remoção da numeração do menu Adm',
)

admin_source = replace_once(
    admin_source,
    "          })}\n        </nav>\n",
    "          })}\n          <button type=\"button\" className=\"domnai-admin-user-menu-entry\" onClick={onUser}>\n            Painel Usuário\n          </button>\n        </nav>\n",
    'Painel Usuário abaixo de Feedbacks no menu Adm',
)

admin_source = replace_once(
    admin_source,
    "      const navigation = document.querySelector('[data-domnai-admin-slot=\"true\"]');\n",
    "      const navigation = document.querySelector('.sidebar-system-group');\n",
    'Destino do botão Painel ADM no menu do usuário',
)

old_user_entry = '''function UserAdminEntry({ onOpen }) {
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
new_user_entry = '''function UserAdminEntry({ onOpen }) {
  return (
    <button
      type="button"
      className="domnai-user-admin-button"
      data-domnai-admin-menu="true"
      onClick={onOpen}
    >
      <span>◇</span>
      Painel ADM
    </button>
  );
}
'''
admin_source = replace_once(
    admin_source,
    old_user_entry,
    new_user_entry,
    'Botão Painel ADM integrado ao menu Sistema',
)

ADMIN.write_text(admin_source, encoding='utf-8')


dashboard_source = DASHBOARD.read_text(encoding='utf-8')

dashboard_source, removed_slots = re.subn(
    r'\n\s*<div className="domnai-user-admin-slot" data-domnai-admin-slot="true" />',
    '',
    dashboard_source,
    count=1,
)
if removed_slots != 1:
    raise SystemExit(f'Remoção do slot antigo do rodapé: esperado 1 trecho, encontrado {removed_slots}.')

dashboard_source = replace_once(
    dashboard_source,
    "<button className={section === 'settings' ? 'is-active' : ''} type=\"button\" onClick={() => openSection('settings')}>",
    "<button data-domnai-settings-menu=\"true\" className={section === 'settings' ? 'is-active' : ''} type=\"button\" onClick={() => openSection('settings')}>",
    'Identificação do botão Configurações para ordenação',
)

DASHBOARD.write_text(dashboard_source, encoding='utf-8')

print('Navegação final alinhada: menus sem números, atalhos cruzados abaixo de Feedback e Brain oculto por estilo final.')
