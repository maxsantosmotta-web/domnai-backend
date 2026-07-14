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
    "import AdminFeedbacksView from './AdminFeedbacksView';\n",
    "import AdminFeedbacksView from './AdminFeedbacksView';\nimport AdminUsersView from './AdminUsersView';\n",
    'Importação do módulo administrativo de usuários',
)

source = replace_once(
    source,
    """  const [activeSection, setActiveSection] = useState(() => {
    const saved = sessionStorage.getItem('domnai:admin-section:v1');
    return saved === 'Feedbacks' ? saved : 'Visão geral';
  });
""",
    """  const [activeSection, setActiveSection] = useState(() => {
    const saved = sessionStorage.getItem('domnai:admin-section:v1');
    return ['Usuários', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';
  });
""",
    'Persistência do módulo Usuários',
)

source = replace_once(
    source,
    "            const enabled = index === 0 || section === 'Feedbacks';\n",
    "            const enabled = index === 0 || section === 'Usuários' || section === 'Feedbacks';\n",
    'Habilitação do módulo Usuários',
)

source = replace_once(
    source,
    """        {activeSection === 'Feedbacks' ? (
          <AdminFeedbacksView />
        ) : (
          <section className="domnai-admin-foundation-card">
""",
    """        {activeSection === 'Usuários' ? (
          <AdminUsersView />
        ) : activeSection === 'Feedbacks' ? (
          <AdminFeedbacksView />
        ) : (
          <section className="domnai-admin-foundation-card">
""",
    'Renderização do módulo Usuários',
)

TARGET.write_text(source, encoding='utf-8')
print('Módulo Usuários conectado ao Painel Adm sem alterar os demais módulos.')
