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
    "import AdminUsersView from './AdminUsersView';\n",
    "import AdminUsersView from './AdminUsersView';\nimport AdminBillingView from './AdminBillingView';\n",
    'Importação do módulo administrativo de faturamento',
)

source = replace_once(
    source,
    """  const [activeSection, setActiveSection] = useState(() => {
    const saved = sessionStorage.getItem('domnai:admin-section:v1');
    return ['Usuários', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';
  });
""",
    """  const [activeSection, setActiveSection] = useState(() => {
    const saved = sessionStorage.getItem('domnai:admin-section:v1');
    return ['Usuários', 'Faturamento', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';
  });
""",
    'Persistência do módulo Faturamento',
)

source = replace_once(
    source,
    "            const enabled = index === 0 || section === 'Usuários' || section === 'Feedbacks';\n",
    "            const enabled = index === 0 || section === 'Usuários' || section === 'Faturamento' || section === 'Feedbacks';\n",
    'Habilitação do módulo Faturamento',
)

source = replace_once(
    source,
    """        {activeSection === 'Usuários' ? (
          <AdminUsersView />
        ) : activeSection === 'Feedbacks' ? (
          <AdminFeedbacksView />
""",
    """        {activeSection === 'Usuários' ? (
          <AdminUsersView />
        ) : activeSection === 'Faturamento' ? (
          <AdminBillingView />
        ) : activeSection === 'Feedbacks' ? (
          <AdminFeedbacksView />
""",
    'Renderização do módulo Faturamento',
)

TARGET.write_text(source, encoding='utf-8')
print('Módulo Faturamento conectado ao Painel Adm sem alterar os demais módulos.')
