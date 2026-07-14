from pathlib import Path
import re

ROOT = Path('/frontend/src')


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'{label}: esperado 1 trecho, encontrado {count}.')
    return source.replace(old, new, 1)


def add_import(source: str, marker: str, addition: str, label: str) -> str:
    if addition.strip() in source:
        return source
    return replace_once(source, marker, f'{marker}{addition}', label)


def insert_after_summary(source: str, class_name: str, content: str, marker: str) -> str:
    if marker in source:
        return source
    pattern = re.compile(
        rf'(<div className="{re.escape(class_name)}"[^>]*>.*?</div>)',
        re.S,
    )
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise SystemExit(f'{class_name}: esperado 1 resumo, encontrado {len(matches)}.')
    match = matches[0]
    return source[:match.end()] + '\n\n' + content + source[match.end():]


# Painel principal e visão geral real.
admin_path = ROOT / 'AdminAccessBoundary.jsx'
admin = admin_path.read_text(encoding='utf-8')
admin = add_import(
    admin,
    "import AdminHealthView from './AdminHealthView';\n",
    "import AdminOverviewView from './AdminOverviewView';\n",
    'Importação da Visão geral premium',
)
admin = add_import(
    admin,
    "import './admin-navigation-final.css';\n",
    "import './admin-premium-monitor.css';\n",
    'Importação do sistema visual premium',
)
if '<AdminOverviewView />' not in admin:
    foundation_pattern = re.compile(
        r'<section className="domnai-admin-foundation-card">.*?</section>',
        re.S,
    )
    matches = list(foundation_pattern.finditer(admin))
    if len(matches) != 1:
        raise SystemExit(f'Visão geral antiga: esperado 1 bloco, encontrado {len(matches)}.')
    match = matches[0]
    admin = admin[:match.start()] + '<AdminOverviewView />' + admin[match.end():]
admin_path.write_text(admin, encoding='utf-8')


# Usuários: linha interativa e distribuição por plano.
users_path = ROOT / 'AdminUsersView.jsx'
users = users_path.read_text(encoding='utf-8')
users = add_import(
    users,
    "import './admin-users-view.css';\n",
    "import { InteractiveDonutChart, InteractiveLineChart } from './AdminPremiumCharts';\n",
    'Importação dos gráficos de Usuários',
)
old_users_analytics = '''          <div className="domnai-admin-users-analytics">
            <article className="analytics-card growth-card">
              <header>
                <div>
                  <span>Crescimento</span>
                  <strong>Novos usuários · últimos 30 dias</strong>
                </div>
                <small>{formatNumber(summary.newThisMonth)} neste mês</small>
              </header>
              <GrowthChart points={growth} />
            </article>

            <article className="analytics-card plan-card">
              <header>
                <div>
                  <span>Planos</span>
                  <strong>Distribuição da base</strong>
                </div>
                <small>{formatNumber(summary.totalUsers)} usuários</small>
              </header>
              <PlanDistribution items={planDistribution} total={summary.totalUsers} />
              <div className="plan-foot">
                <span>Perfis completos <strong>{formatNumber(summary.profileCompleted)}</strong></span>
                <span>Créditos na base <strong>{formatNumber(summary.totalCredits)}</strong></span>
              </div>
            </article>
          </div>
'''
new_users_analytics = '''          <div className="domnai-premium-chart-grid users-premium-charts">
            <InteractiveLineChart
              title="Crescimento de usuários"
              subtitle="Últimos 30 dias"
              data={growth.map((item) => ({ label: item.label, value: item.count }))}
              primaryLabel="Novos usuários"
            />
            <InteractiveDonutChart
              title="Distribuição da base"
              subtitle="Planos atuais"
              data={planDistribution.map((item) => ({ label: item.label, value: item.count }))}
              centerLabel="Usuários"
            />
          </div>
'''
if 'users-premium-charts' not in users:
    users = replace_once(users, old_users_analytics, new_users_analytics, 'Gráficos premium de Usuários')
users_path.write_text(users, encoding='utf-8')


# Faturamento: pulso financeiro e distribuição dos planos.
billing_path = ROOT / 'AdminBillingView.jsx'
billing = billing_path.read_text(encoding='utf-8')
billing = add_import(
    billing,
    "import './admin-billing-view.css';\n",
    "import { InteractiveBarChart, InteractiveDonutChart } from './AdminPremiumCharts';\n",
    'Importação dos gráficos de Faturamento',
)
billing_charts = '''      <div className="domnai-premium-chart-grid billing-premium-charts">
        <InteractiveBarChart
          title="Pulso financeiro"
          subtitle="Valores atuais"
          data={[
            { label: 'Receita do mês', value: summary.revenueMonthCents, color: '#64e6a6' },
            { label: 'Receita recorrente', value: summary.mrrCents, color: '#f4c95d' },
            { label: 'Valor pendente', value: summary.pendingAmountCents, color: '#ff657f' },
          ]}
          valueFormatter={formatMoney}
        />
        <InteractiveDonutChart
          title="Distribuição de planos"
          subtitle="Base financeira"
          data={[
            { label: 'Premium', value: summary.premiumPlans, color: '#f4c95d' },
            { label: 'Free', value: summary.freePlans, color: '#3fd7ff' },
            { label: 'Sem plano', value: summary.unselectedPlans, color: '#9b82ff' },
          ]}
          centerLabel="Contas"
        />
      </div>'''
billing = insert_after_summary(billing, 'domnai-admin-billing-summary', billing_charts, 'billing-premium-charts')
billing_path.write_text(billing, encoding='utf-8')


# Erros e alertas: intensidade e estado dos grupos.
errors_path = ROOT / 'AdminErrorsView.jsx'
errors = errors_path.read_text(encoding='utf-8')
errors = add_import(
    errors,
    "import './admin-errors-view.css';\n",
    "import { InteractiveBarChart, InteractiveDonutChart } from './AdminPremiumCharts';\n",
    'Importação dos gráficos de Erros',
)
errors_charts = '''      <div className="domnai-premium-chart-grid errors-premium-charts">
        <InteractiveBarChart
          title="Intensidade operacional"
          subtitle="Ocorrências e grupos"
          data={[
            { label: 'Ocorrências', value: summary.totalOccurrences, color: '#ff657f' },
            { label: 'Erros ativos', value: summary.activeGroups, color: '#ff9f5a' },
            { label: 'Críticos', value: summary.criticalGroups, color: '#ff5cc8' },
            { label: 'Módulos afetados', value: summary.affectedModules, color: '#9b82ff' },
          ]}
        />
        <InteractiveDonutChart
          title="Estado dos grupos"
          subtitle="Situação atual"
          data={[
            { label: 'Ativos', value: summary.activeGroups, color: '#ff657f' },
            { label: 'Estabilizados', value: summary.stableGroups, color: '#f4c95d' },
            { label: 'Resolvidos', value: summary.resolvedGroups, color: '#64e6a6' },
          ]}
          centerLabel="Grupos"
        />
      </div>'''
errors = insert_after_summary(errors, 'domnai-admin-errors-summary', errors_charts, 'errors-premium-charts')
errors_path.write_text(errors, encoding='utf-8')


# Auditoria: ações individuais e balanço operacional.
audit_path = ROOT / 'AdminAuditView.jsx'
audit = audit_path.read_text(encoding='utf-8')
audit = add_import(
    audit,
    "import './admin-audit-view.css';\n",
    "import { InteractiveBarChart, InteractiveDonutChart } from './AdminPremiumCharts';\n",
    'Importação dos gráficos de Auditoria',
)
audit_charts = '''      <div className="domnai-premium-chart-grid audit-premium-charts">
        <InteractiveBarChart
          title="Ações auditadas"
          subtitle="Contadores funcionais"
          data={[
            { label: 'Planos', value: summary.planChanges },
            { label: 'Pagamentos aprovados', value: summary.paymentsApproved },
            { label: 'Pagamentos recusados', value: summary.paymentsFailed },
            { label: 'Cancelamentos', value: summary.subscriptionsCanceled },
            { label: 'Créditos adicionados', value: summary.creditsAdded },
            { label: 'Créditos consumidos', value: summary.creditsConsumed },
            { label: 'PDFs concluídos', value: summary.pdfsDelivered },
          ]}
        />
        <InteractiveDonutChart
          title="Balanço das ações"
          subtitle="Concluídas e atenções"
          data={[
            { label: 'Concluídas', value: summary.planChanges + summary.paymentsApproved + summary.creditsAdded + summary.creditsConsumed + summary.pdfsDelivered, color: '#64e6a6' },
            { label: 'Recusadas', value: summary.paymentsFailed, color: '#ff657f' },
            { label: 'Canceladas', value: summary.subscriptionsCanceled, color: '#ff9f5a' },
          ]}
          centerLabel="Eventos"
        />
      </div>'''
audit = insert_after_summary(audit, 'domnai-admin-audit-summary', audit_charts, 'audit-premium-charts')
audit_path.write_text(audit, encoding='utf-8')


# Saúde operacional: histórico real de latência por atualização.
health_path = ROOT / 'AdminHealthView.jsx'
health = health_path.read_text(encoding='utf-8')
health = add_import(
    health,
    "import './admin-health-view.css';\n",
    "import { InteractiveDonutChart, InteractiveLineChart } from './AdminPremiumCharts';\n",
    'Importação dos gráficos de Saúde operacional',
)
if 'latencyHistory' not in health:
    health = replace_once(
        health,
        "  const [apiLatency, setApiLatency] = useState(null);\n",
        "  const [apiLatency, setApiLatency] = useState(null);\n  const [latencyHistory, setLatencyHistory] = useState([]);\n",
        'Estado do histórico de latência',
    )
    health = replace_once(
        health,
        "      setApiLatency(measuredLatency);\n      setStatus('ready');\n",
        "      setApiLatency(measuredLatency);\n      const databaseLatency = Number(payload?.dependencies?.database?.latencyMs ?? 0);\n      const timestamp = new Date();\n      setLatencyHistory((current) => [...current, {\n        label: timestamp.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),\n        value: measuredLatency,\n        secondaryValue: databaseLatency,\n      }].slice(-24));\n      setStatus('ready');\n",
        'Registro real da latência',
    )
health_charts = '''
      <div className="domnai-premium-chart-grid health-premium-charts">
        <InteractiveLineChart
          title="Latência ao vivo"
          subtitle="Últimas verificações"
          data={latencyHistory}
          valueFormatter={latencyLabel}
          primaryLabel="API"
          secondaryLabel="Banco"
        />
        <InteractiveDonutChart
          title="Disponibilidade atual"
          subtitle="Serviços monitorados"
          data={[
            { label: 'Prontos', value: readyCount, color: '#64e6a6' },
            { label: 'Atenções', value: attentionCount, color: '#ff9f5a' },
          ]}
          centerLabel="Serviços"
        />
      </div>'''
if 'health-premium-charts' not in health:
    overall_pattern = re.compile(
        r'(<section className=\{`domnai-admin-health-overall .*?</section>)',
        re.S,
    )
    matches = list(overall_pattern.finditer(health))
    if len(matches) != 1:
        raise SystemExit(f'Saúde geral: esperado 1 bloco, encontrado {len(matches)}.')
    match = matches[0]
    health = health[:match.end()] + health_charts + health[match.end():]
health_path.write_text(health, encoding='utf-8')


# Feedbacks: atualização automática e leitura visual dos tipos.
feedback_path = ROOT / 'AdminFeedbacksView.jsx'
feedback = feedback_path.read_text(encoding='utf-8')
feedback = add_import(
    feedback,
    "import './admin-feedbacks-refine.css';\n",
    "import { InteractiveBarChart, InteractiveDonutChart } from './AdminPremiumCharts';\n",
    'Importação dos gráficos de Feedbacks',
)
if 'silent = false' not in feedback:
    feedback = replace_once(
        feedback,
        "  const loadFeedbacks = useCallback(async () => {\n    setStatus('loading');\n    setError('');\n",
        "  const loadFeedbacks = useCallback(async ({ silent = false } = {}) => {\n    if (!silent) setStatus('loading');\n    setError('');\n",
        'Carregamento silencioso dos Feedbacks',
    )
    feedback = replace_once(
        feedback,
        "    } catch (loadError) {\n      setError(loadError?.message || 'Não foi possível carregar os feedbacks.');\n      setStatus('error');\n    }\n",
        "    } catch (loadError) {\n      if (!silent) {\n        setError(loadError?.message || 'Não foi possível carregar os feedbacks.');\n        setStatus('error');\n      }\n    }\n",
        'Falha silenciosa dos Feedbacks',
    )
    feedback = replace_once(
        feedback,
        "  useEffect(() => {\n    loadFeedbacks();\n  }, [loadFeedbacks]);\n",
        "  useEffect(() => {\n    loadFeedbacks();\n    const interval = window.setInterval(() => loadFeedbacks({ silent: true }), 15000);\n    return () => window.clearInterval(interval);\n  }, [loadFeedbacks]);\n",
        'Atualização automática dos Feedbacks',
    )
feedback_charts = '''      <div className="domnai-premium-chart-grid feedback-premium-charts">
        <InteractiveDonutChart
          title="Distribuição dos feedbacks"
          subtitle="Tipos recebidos"
          data={[
            { label: 'Sugestões', value: summary.suggestions, color: '#3fd7ff' },
            { label: 'Problemas', value: summary.problems, color: '#ff657f' },
            { label: 'Elogios', value: summary.praises, color: '#f4c95d' },
          ]}
          centerLabel="Feedbacks"
        />
        <InteractiveBarChart
          title="Qualidade percebida"
          subtitle="Avaliação média"
          data={[
            { label: 'Média atual', value: summary.average, color: '#f4c95d' },
            { label: 'Referência máxima', value: 5, color: '#9b82ff' },
          ]}
          valueFormatter={(value) => Number(value || 0).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
        />
      </div>'''
feedback = insert_after_summary(feedback, 'domnai-admin-feedbacks-summary', feedback_charts, 'feedback-premium-charts')
feedback_path.write_text(feedback, encoding='utf-8')

print('Painel Adm modernizado com identidade premium, gráficos interativos e dados reais em todos os módulos.')
