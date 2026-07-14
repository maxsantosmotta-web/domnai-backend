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
    "import AdminErrorsView from './AdminErrorsView';\n",
    "import AdminErrorsView from './AdminErrorsView';\nimport AdminAuditView from './AdminAuditView';\n",
    'Importação do módulo administrativo de auditoria',
)

source = replace_once(
    source,
    "return ['Usuários', 'Faturamento', 'Erros e alertas', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';",
    "return ['Usuários', 'Faturamento', 'Erros e alertas', 'Auditoria', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';",
    'Persistência do módulo Auditoria',
)

source = replace_once(
    source,
    "const enabled = index === 0 || section === 'Usuários' || section === 'Faturamento' || section === 'Erros e alertas' || section === 'Feedbacks';",
    "const enabled = index === 0 || section === 'Usuários' || section === 'Faturamento' || section === 'Erros e alertas' || section === 'Auditoria' || section === 'Feedbacks';",
    'Habilitação do módulo Auditoria',
)

source = replace_once(
    source,
    """        ) : activeSection === 'Erros e alertas' ? (
          <AdminErrorsView />
        ) : activeSection === 'Feedbacks' ? (
""",
    """        ) : activeSection === 'Erros e alertas' ? (
          <AdminErrorsView />
        ) : activeSection === 'Auditoria' ? (
          <AdminAuditView />
        ) : activeSection === 'Feedbacks' ? (
""",
    'Renderização do módulo Auditoria',
)

TARGET.write_text(source, encoding='utf-8')
print('Módulo Auditoria conectado ao Painel Adm sem alterar os demais módulos.')
