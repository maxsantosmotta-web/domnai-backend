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
    "import AdminAuditView from './AdminAuditView';\n",
    "import AdminAuditView from './AdminAuditView';\nimport AdminHealthView from './AdminHealthView';\n",
    'Importação do módulo Saúde operacional',
)

source = replace_once(
    source,
    "return ['Usuários', 'Faturamento', 'Erros e alertas', 'Auditoria', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';",
    "return ['Usuários', 'Faturamento', 'Erros e alertas', 'Auditoria', 'Saúde operacional', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';",
    'Persistência do módulo Saúde operacional',
)

source = replace_once(
    source,
    "const enabled = index === 0 || section === 'Usuários' || section === 'Faturamento' || section === 'Erros e alertas' || section === 'Auditoria' || section === 'Feedbacks';",
    "const enabled = index === 0 || section === 'Usuários' || section === 'Faturamento' || section === 'Erros e alertas' || section === 'Auditoria' || section === 'Saúde operacional' || section === 'Feedbacks';",
    'Habilitação do módulo Saúde operacional',
)

source = replace_once(
    source,
    """        ) : activeSection === 'Auditoria' ? (
          <AdminAuditView />
        ) : activeSection === 'Feedbacks' ? (
""",
    """        ) : activeSection === 'Auditoria' ? (
          <AdminAuditView />
        ) : activeSection === 'Saúde operacional' ? (
          <AdminHealthView />
        ) : activeSection === 'Feedbacks' ? (
""",
    'Renderização do módulo Saúde operacional',
)

TARGET.write_text(source, encoding='utf-8')
print('Módulo Saúde operacional conectado ao Painel Adm sem alterar os demais módulos.')
