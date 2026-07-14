from pathlib import Path

TARGET = Path('/frontend/src/AdminAccessBoundary.jsx')


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'{label}: esperado 1 trecho, encontrado {count}.')
    return source.replace(old, new, 1)


source = TARGET.read_text(encoding='utf-8')

source = replace_once(
    source,
    "import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';\n",
    "import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';\nimport AdminFeedbacksView from './AdminFeedbacksView';\n",
    'Importação do módulo administrativo de feedbacks',
)

source = replace_once(
    source,
    """function AdminPortalShell({ onUser, onSignOut, profile, user, avatarUrl }) {
  const [menuOpen, setMenuOpen] = useState(isWideAdminViewport);
""",
    """function AdminPortalShell({ onUser, onSignOut, profile, user, avatarUrl }) {
  const [menuOpen, setMenuOpen] = useState(isWideAdminViewport);
  const [activeSection, setActiveSection] = useState(() => {
    const saved = sessionStorage.getItem('domnai:admin-section:v1');
    return saved === 'Feedbacks' ? saved : 'Visão geral';
  });
""",
    'Estado da função administrativa ativa',
)

source = replace_once(
    source,
    """  function selectOverview() {
    if (!isWideAdminViewport()) setMenuOpen(false);
  }
""",
    """  function selectSection(section) {
    setActiveSection(section);
    sessionStorage.setItem('domnai:admin-section:v1', section);
    if (!isWideAdminViewport()) setMenuOpen(false);
  }
""",
    'Seleção de função administrativa',
)

source = replace_once(
    source,
    """          {ADMIN_SECTIONS.map((section, index) => (
            <button
              type="button"
              key={section}
              disabled={index !== 0}
              onClick={index === 0 ? selectOverview : undefined}
            >
              <span>{String(index + 1).padStart(2, '0')}</span>
              {section}
            </button>
          ))}
""",
    """          {ADMIN_SECTIONS.map((section, index) => {
            const enabled = index === 0 || section === 'Feedbacks';
            const selected = activeSection === section;
            return (
              <button
                type="button"
                className={selected ? 'active-section' : ''}
                aria-current={selected ? 'page' : undefined}
                key={section}
                disabled={!enabled}
                onClick={enabled ? () => selectSection(section) : undefined}
              >
                <span>{String(index + 1).padStart(2, '0')}</span>
                {section}
              </button>
            );
          })}
""",
    'Menu administrativo habilitado',
)

source = replace_once(
    source,
    '<header className="domnai-admin-topbar">\n',
    '<header className={`domnai-admin-topbar ${menuOpen ? \'is-empty\' : \'\'}`}>\n',
    'Estado visual do cabeçalho administrativo',
)

source = replace_once(
    source,
    """            <div>
              <span>DomnAI · Administração</span>
              <h1>Visão geral</h1>
            </div>
""",
    """            <div className="domnai-admin-context-spacer" aria-hidden="true" />
""",
    'Remoção do título repetido do conteúdo administrativo',
)

source = replace_once(
    source,
    """        <section className="domnai-admin-foundation-card">
          <span className="domnai-admin-foundation-kicker">Fase 1</span>
          <h2>Ambiente administrativo isolado</h2>
          <p>
            A estrutura de acesso foi separada do ambiente dos usuários. Os dados, gráficos e recursos de monitoramento serão conectados nas próximas etapas sem alterar o Dashboard do cliente.
          </p>
          <div className="domnai-admin-foundation-status">
            <span><strong>Proteção</strong> validação administrativa no backend</span>
            <span><strong>Usuário</strong> experiência atual preservada</span>
            <span><strong>Adm</strong> arquivos e estilos exclusivos</span>
          </div>
        </section>
""",
    """        {activeSection === 'Feedbacks' ? (
          <AdminFeedbacksView />
        ) : (
          <section className="domnai-admin-foundation-card">
            <span className="domnai-admin-foundation-kicker">Fase 1</span>
            <h2>Ambiente administrativo isolado</h2>
            <p>
              A estrutura de acesso foi separada do ambiente dos usuários. Os dados, gráficos e recursos de monitoramento serão conectados nas próximas etapas sem alterar o Dashboard do cliente.
            </p>
            <div className="domnai-admin-foundation-status">
              <span><strong>Proteção</strong> validação administrativa no backend</span>
              <span><strong>Usuário</strong> experiência atual preservada</span>
              <span><strong>Adm</strong> arquivos e estilos exclusivos</span>
            </div>
          </section>
        )}
""",
    'Conteúdo da função Feedbacks',
)

TARGET.write_text(source, encoding='utf-8')
print('Feedbacks administrativos conectados com indicação pelo menu e sem títulos repetidos.')
