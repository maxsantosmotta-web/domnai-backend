from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

css_import = "import './user-sidebar-collapse.css';"
if css_import not in source:
    marker = "import './mobile-chat-keyboard.css';"
    if marker not in source:
        marker = "import './dashboard-adjustments.css';"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar os estilos-base do Dashboard.')
    source = source.replace(marker, marker + "\n" + css_import, 1)

state_line = "  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);"
if state_line not in source:
    marker = "  const [sidebarOpen, setSidebarOpen] = useState(false);"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o estado do menu lateral.')
    source = source.replace(marker, marker + "\n" + state_line, 1)

source = source.replace(
    '<main className="domnai-app-shell">',
    '<main className={`domnai-app-shell${sidebarCollapsed ? \' user-sidebar-collapsed\' : \'\'}`}>',
    1,
)

old_menu_button = '<button type="button" className="mobile-menu-button" aria-label="Abrir dashboard" onClick={() => setSidebarOpen(true)}>☰</button>'
new_menu_button = '<button type="button" className="mobile-menu-button" aria-label="Abrir dashboard" onClick={() => { setSidebarCollapsed(false); setSidebarOpen(true); }}>☰</button>'
if old_menu_button in source:
    source = source.replace(old_menu_button, new_menu_button, 1)
elif new_menu_button not in source:
    raise RuntimeError('Não foi possível localizar o botão de abertura do menu.')

old_brand = '<div className="sidebar-brand"><img src={DOMNAI_LOGO} alt="DomnAI" /><button type="button" className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu">×</button></div>'
new_brand = '<div className="sidebar-brand"><img src={DOMNAI_LOGO} alt="DomnAI" /><button type="button" className="user-sidebar-collapse-button" onClick={() => { setSidebarCollapsed(true); setSidebarOpen(false); }} aria-label="Recolher menu lateral">×</button><button type="button" className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu">×</button></div>'
if old_brand in source:
    source = source.replace(old_brand, new_brand, 1)
elif 'user-sidebar-collapse-button' not in source:
    raise RuntimeError('Não foi possível localizar o cabeçalho do menu lateral.')

path.write_text(source, encoding='utf-8')
