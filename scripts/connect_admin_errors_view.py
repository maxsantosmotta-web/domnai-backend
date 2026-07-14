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
    "import AdminBillingView from './AdminBillingView';\n",
    "import AdminBillingView from './AdminBillingView';\nimport AdminErrorsView from './AdminErrorsView';\n",
    'Importação do módulo administrativo de erros e alertas',
)

source = replace_once(
    source,
    "return ['Usuários', 'Faturamento', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';",
    "return ['Usuários', 'Faturamento', 'Erros e alertas', 'Feedbacks'].includes(saved) ? saved : 'Visão geral';",
    'Persistência do módulo Erros e alertas',
)

source = replace_once(
    source,
    "const enabled = index === 0 || section === 'Usuários' || section === 'Faturamento' || section === 'Feedbacks';",
    "const enabled = index === 0 || section === 'Usuários' || section === 'Faturamento' || section === 'Erros e alertas' || section === 'Feedbacks';",
    'Habilitação do módulo Erros e alertas',
)

source = replace_once(
    source,
    """        ) : activeSection === 'Faturamento' ? (
          <AdminBillingView />
        ) : activeSection === 'Feedbacks' ? (
""",
    """        ) : activeSection === 'Faturamento' ? (
          <AdminBillingView />
        ) : activeSection === 'Erros e alertas' ? (
          <AdminErrorsView />
        ) : activeSection === 'Feedbacks' ? (
""",
    'Renderização do módulo Erros e alertas',
)

TARGET.write_text(source, encoding='utf-8')
print('Módulo Erros e alertas conectado ao Painel Adm sem alterar os demais módulos.')
