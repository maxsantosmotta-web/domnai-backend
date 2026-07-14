import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import './admin-billing-view.css';

const EMPTY_SUMMARY = {
  totalAccounts: 0,
  customerUsers: 0,
  premiumPlans: 0,
  freePlans: 0,
  unselectedPlans: 0,
  paidSubscriptions: 0,
  overdueAccounts: 0,
  mrrCents: 0,
  revenueMonthCents: 0,
  paidInvoicesMonth: 0,
  pendingInvoices: 0,
  pendingAmountCents: 0,
  webhookEvents24h: 0,
  processedEvents: 0,
};

const PLAN_FILTERS = [
  { value: 'all', label: 'Todos os planos' },
  { value: 'free', label: 'Plano Free' },
  { value: 'premium', label: 'Plano Premium' },
  { value: 'unselected', label: 'Sem plano' },
];

const STATUS_FILTERS = [
  { value: 'all', label: 'Todos os status' },
  { value: 'active', label: 'Ativa' },
  { value: 'trialing', label: 'Em teste' },
  { value: 'past_due', label: 'Em atraso' },
  { value: 'unpaid', label: 'Não paga' },
  { value: 'inactive', label: 'Inativa' },
  { value: 'canceled', label: 'Cancelada' },
];

function formatNumber(value) {
  return Number(value || 0).toLocaleString('pt-BR');
}

function formatMoney(cents) {
  return (Number(cents || 0) / 100).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

function formatDate(value, withTime = false) {
  if (!value) return 'Sem registro';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Sem registro';
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  });
}

function initials(name) {
  return String(name || 'U')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('') || 'U';
}

async function readResponse(response) {
  const raw = await response.text();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { detail: raw };
  }
}

function exportAccountsCsv(items) {
  const header = [
    'Nome', 'E-mail', 'Função', 'Plano', 'Status da assinatura',
    'Mensalidade estimada', 'Créditos do plano', 'Créditos extras',
    'Créditos totais', 'Próxima renovação', 'Última atualização',
  ];
  const rows = items.map((item) => [
    item.name,
    item.email,
    item.roleLabel,
    item.planLabel,
    item.subscriptionStatusLabel,
    formatMoney(item.monthlyAmountCents),
    item.planCredits,
    item.extraCredits,
    item.totalCredits,
    formatDate(item.currentPeriodEnd, true),
    formatDate(item.updatedAt, true),
  ]);
  const escape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
  const csv = [header, ...rows].map((row) => row.map(escape).join(';')).join('\n');
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `domnai-faturamento-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function StatusBadge({ status, label }) {
  return <span className={`billing-status-badge ${status || 'inactive'}`}>{label}</span>;
}

export default function AdminBillingView() {
  const { getToken } = useAuth();
  const [items, setItems] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [brainInsights, setBrainInsights] = useState([]);
  const [stripeState, setStripeState] = useState({ configured: false, connected: false, statusLabel: 'Conectando...' });
  const [generatedAt, setGeneratedAt] = useState('');
  const [dataWarning, setDataWarning] = useState('');
  const [query, setQuery] = useState('');
  const [planFilter, setPlanFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  const loadBilling = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setStatus('loading');
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Não foi possível validar a sessão administrativa.');
      const response = await fetch('/api/admin/billing?limit=1000', {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      const payload = await readResponse(response);
      if (!response.ok) throw new Error(payload.detail || `Falha ao carregar faturamento (${response.status}).`);
      setItems(Array.isArray(payload.items) ? payload.items : []);
      setInvoices(Array.isArray(payload.invoices) ? payload.invoices : []);
      setTransactions(Array.isArray(payload.transactions) ? payload.transactions : []);
      setSummary({ ...EMPTY_SUMMARY, ...(payload.summary || {}) });
      setBrainInsights(Array.isArray(payload.brainInsights) ? payload.brainInsights : []);
      setStripeState(payload.stripe || { configured: false, connected: false, statusLabel: 'Indisponível' });
      setGeneratedAt(payload.generatedAt || new Date().toISOString());
      setDataWarning(String(payload.dataWarning || ''));
      setStatus('ready');
    } catch (loadError) {
      if (!silent) {
        setError(loadError?.message || 'Não foi possível carregar o faturamento.');
        setStatus('error');
      }
    }
  }, [getToken]);

  useEffect(() => {
    loadBilling();
    const interval = window.setInterval(() => loadBilling({ silent: true }), 30000);
    return () => window.clearInterval(interval);
  }, [loadBilling]);

  const visibleItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return items.filter((item) => {
      const matchesSearch = !normalizedQuery
        || String(item.name || '').toLowerCase().includes(normalizedQuery)
        || String(item.email || '').toLowerCase().includes(normalizedQuery);
      const matchesPlan = planFilter === 'all' || item.plan === planFilter;
      const matchesStatus = statusFilter === 'all' || item.subscriptionStatus === statusFilter;
      return matchesSearch && matchesPlan && matchesStatus;
    });
  }, [items, planFilter, query, statusFilter]);

  const visibleBrainInsights = useMemo(() => {
    const customerIds = new Set(
      items.filter((item) => item.role !== 'admin').map((item) => item.id),
    );
    const cutoff = Date.now() - (30 * 24 * 60 * 60 * 1000);
    const consumption = transactions.filter((item) => {
      const createdAt = new Date(item.createdAt || 0).getTime();
      return item.kind === 'consumption'
        && Number(item.amount || 0) < 0
        && customerIds.has(item.userId)
        && Number.isFinite(createdAt)
        && createdAt >= cutoff;
    });

    if (consumption.length === 0) return brainInsights;

    const consumedCredits = consumption.reduce(
      (total, item) => total + Math.abs(Number(item.amount || 0)),
      0,
    );
    const consumers = new Set(consumption.map((item) => item.userId)).size;
    const consumptionInsight = {
      level: 'info',
      title: 'Consumo de créditos',
      message: `${formatNumber(consumedCredits)} crédito(s) utilizados por ${formatNumber(consumers)} cliente(s) nos últimos 30 dias.`,
    };

    return [consumptionInsight, ...brainInsights].slice(0, 4);
  }, [brainInsights, items, transactions]);

  function handleRefresh(event) {
    event.currentTarget.blur();
    loadBilling();
  }

  function handleExport(event) {
    event.currentTarget.blur();
    exportAccountsCsv(visibleItems);
  }

  return (
    <section className="domnai-admin-billing-view" aria-label="Faturamento administrativo">
      <header className="domnai-admin-billing-heading">
        <div className="billing-live-copy">
          <span className="billing-live-indicator"><i />Dados reais · atualização automática</span>
          <small>{generatedAt ? `Última atualização: ${formatDate(generatedAt, true)}` : 'Conectando dados...'}</small>
        </div>
        <div className="billing-heading-actions">
          <button type="button" onClick={handleExport} disabled={status !== 'ready' || visibleItems.length === 0}>Exportar CSV</button>
          <button type="button" onClick={handleRefresh} disabled={status === 'loading'}>{status === 'loading' ? 'Atualizando...' : 'Atualizar'}</button>
        </div>
      </header>

      <div className="domnai-admin-billing-summary" aria-label="Resumo financeiro">
        <article><span>Receita neste mês</span><strong>{formatMoney(summary.revenueMonthCents)}</strong></article>
        <article><span>Receita recorrente mensal</span><strong>{formatMoney(summary.mrrCents)}</strong></article>
        <article><span>Assinaturas pagas</span><strong>{formatNumber(summary.paidSubscriptions)}</strong></article>
        <article><span>Plano Premium</span><strong>{formatNumber(summary.premiumPlans)}</strong></article>
        <article><span>Plano Free</span><strong>{formatNumber(summary.freePlans)}</strong></article>
        <article><span>Pendências financeiras</span><strong>{formatNumber(summary.pendingInvoices + summary.overdueAccounts)}</strong></article>
      </div>

      {dataWarning ? (
        <div className="domnai-admin-billing-warning" role="status">
          <strong>Atualização parcial</strong>
          <span>{dataWarning}</span>
        </div>
      ) : null}

      {status === 'loading' ? (
        <div className="domnai-admin-billing-state"><span className="billing-spinner" />Carregando dados financeiros reais...</div>
      ) : null}

      {status === 'error' ? (
        <div className="domnai-admin-billing-state error">
          <strong>Não foi possível carregar o módulo Faturamento.</strong>
          <p>{error}</p>
          <button type="button" onClick={() => loadBilling()}>Tentar novamente</button>
        </div>
      ) : null}

      {status === 'ready' ? (
        <>
          <div className="domnai-admin-billing-operation-grid">
            <article className="billing-operation-card">
              <header><span>Operação financeira</span><strong>Estado atual</strong></header>
              <div className="billing-operation-list">
                <div><span>Stripe</span><strong className={stripeState.connected ? 'positive' : 'attention'}>{stripeState.statusLabel}</strong></div>
                <div><span>Faturas pagas no mês</span><strong>{formatNumber(summary.paidInvoicesMonth)}</strong></div>
                <div><span>Faturas pendentes</span><strong>{formatNumber(summary.pendingInvoices)}</strong></div>
                <div><span>Valor pendente</span><strong>{formatMoney(summary.pendingAmountCents)}</strong></div>
              </div>
            </article>

            <article className="billing-operation-card">
              <header><span>Sincronização</span><strong>Webhooks e base</strong></header>
              <div className="billing-operation-list">
                <div><span>Eventos nas últimas 24h</span><strong>{formatNumber(summary.webhookEvents24h)}</strong></div>
                <div><span>Eventos processados</span><strong>{formatNumber(summary.processedEvents)}</strong></div>
                <div><span>Contas atuais</span><strong>{formatNumber(summary.totalAccounts)}</strong></div>
                <div><span>Usuários clientes</span><strong>{formatNumber(summary.customerUsers)}</strong></div>
              </div>
            </article>
          </div>

          <section className="domnai-admin-billing-brain" aria-label="Leitura IAttom Brain do faturamento">
            <header>
              <div className="billing-brain-mark">IB</div>
              <div><span>IAttom Brain</span><strong>Leitura automática da operação financeira</strong></div>
            </header>
            <div className="billing-brain-grid">
              {visibleBrainInsights.map((insight, index) => (
                <article className={insight.level || 'info'} key={`${insight.title}-${index}`}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div><strong>{insight.title}</strong><p>{insight.message}</p></div>
                </article>
              ))}
            </div>
          </section>

          <div className="domnai-admin-billing-toolbar">
            <label>
              <span>Buscar conta</span>
              <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nome ou e-mail" />
            </label>
            <label>
              <span>Plano</span>
              <select value={planFilter} onChange={(event) => setPlanFilter(event.target.value)}>
                {PLAN_FILTERS.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              <span>Status</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                {STATUS_FILTERS.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
              </select>
            </label>
            <div className="billing-result-count"><span>Exibindo</span><strong>{formatNumber(visibleItems.length)} de {formatNumber(items.length)}</strong></div>
          </div>

          <section className="domnai-admin-billing-section-card">
            <header><div><span>Contas e assinaturas</span><strong>Planos, cobrança e renovação</strong></div></header>
            {visibleItems.length === 0 ? (
              <div className="domnai-admin-billing-state compact"><strong>Nenhuma conta encontrada</strong><p>Ajuste a busca ou os filtros aplicados.</p></div>
            ) : (
              <div className="domnai-admin-billing-table-wrap">
                <table className="domnai-admin-billing-table accounts-table">
                  <thead><tr><th>Conta</th><th>Função</th><th>Plano</th><th>Status</th><th>Mensalidade</th><th>Créditos</th><th>Renovação</th></tr></thead>
                  <tbody>
                    {visibleItems.map((item) => (
                      <tr key={item.id}>
                        <td><div className="billing-user-cell"><span>{initials(item.name)}</span><div><strong>{item.name}</strong><small>{item.email || 'E-mail não disponível'}</small></div></div></td>
                        <td><span className={`billing-role-badge ${item.role}`}>{item.roleLabel}</span></td>
                        <td><strong>{item.planLabel}</strong></td>
                        <td><StatusBadge status={item.subscriptionStatus} label={item.subscriptionStatusLabel} /></td>
                        <td><strong>{formatMoney(item.monthlyAmountCents)}</strong></td>
                        <td><strong>{formatNumber(item.totalCredits)}</strong></td>
                        <td><time dateTime={item.currentPeriodEnd || undefined}>{formatDate(item.currentPeriodEnd)}</time></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="domnai-admin-billing-section-card">
            <header><div><span>Faturas recentes</span><strong>Pagamentos vinculados aos clientes atuais</strong></div><small>{formatNumber(invoices.length)} registro(s)</small></header>
            {invoices.length === 0 ? (
              <div className="domnai-admin-billing-empty">Nenhuma fatura financeira vinculada aos usuários atuais.</div>
            ) : (
              <div className="domnai-admin-billing-table-wrap">
                <table className="domnai-admin-billing-table invoices-table">
                  <thead><tr><th>Cliente</th><th>Fatura</th><th>Status</th><th>Pago</th><th>Pendente</th><th>Data</th></tr></thead>
                  <tbody>{invoices.map((item) => (
                    <tr key={item.id}><td><strong>{item.name}</strong><small>{item.email}</small></td><td>{item.number}</td><td><StatusBadge status={item.status} label={item.statusLabel} /></td><td>{formatMoney(item.amountPaidCents)}</td><td>{formatMoney(item.amountRemainingCents)}</td><td>{formatDate(item.createdAt, true)}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </section>
  );
}
