import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { InteractiveBarChart, InteractiveDonutChart, InteractiveLineChart } from './AdminPremiumCharts';

const EMPTY_DATA = {
  users: {},
  billing: {},
  errors: {},
  audit: {},
  feedbacks: {},
  health: {},
};

function formatNumber(value) {
  return Number(value || 0).toLocaleString('pt-BR');
}

function formatMoney(cents) {
  return (Number(cents || 0) / 100).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  });
}

function formatDate(value) {
  if (!value) return 'Sem atualização';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Sem atualização';
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

async function readResponse(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export default function AdminOverviewView() {
  const { getToken } = useAuth();
  const [data, setData] = useState(EMPTY_DATA);
  const [status, setStatus] = useState('loading');
  const [generatedAt, setGeneratedAt] = useState('');
  const [warning, setWarning] = useState('');

  const loadOverview = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setStatus('loading');
    setWarning('');

    try {
      const token = await getToken();
      if (!token) throw new Error('Não foi possível validar a sessão administrativa.');
      const authorizedHeaders = { Authorization: `Bearer ${token}` };
      const requests = [
        ['users', '/api/admin/users?limit=1000', authorizedHeaders],
        ['billing', '/api/admin/billing?limit=1000', authorizedHeaders],
        ['errors', '/api/admin/errors?limit=2000', authorizedHeaders],
        ['audit', '/api/admin/audit?limit=100', authorizedHeaders],
        ['feedbacks', '/api/feedback/admin?limit=200', authorizedHeaders],
        ['health', '/health', {}],
      ];

      const results = await Promise.allSettled(requests.map(async ([key, url, headers]) => {
        const response = await fetch(url, { headers, cache: 'no-store' });
        const payload = await readResponse(response);
        if (!response.ok) throw new Error(`${key}: ${payload.detail || response.status}`);
        return [key, payload];
      }));

      const next = { ...EMPTY_DATA };
      const failed = [];
      results.forEach((result, index) => {
        const key = requests[index][0];
        if (result.status === 'fulfilled') next[result.value[0]] = result.value[1];
        else failed.push(key);
      });

      setData(next);
      setGeneratedAt(new Date().toISOString());
      setWarning(failed.length ? `Atualização parcial: ${failed.join(', ')}.` : '');
      setStatus('ready');
    } catch (loadError) {
      if (!silent) {
        setWarning(loadError?.message || 'Não foi possível carregar a visão geral.');
        setStatus('error');
      }
    }
  }, [getToken]);

  useEffect(() => {
    loadOverview();
    const interval = window.setInterval(() => loadOverview({ silent: true }), 15000);
    return () => window.clearInterval(interval);
  }, [loadOverview]);

  const usersSummary = data.users?.summary || {};
  const billingSummary = data.billing?.summary || {};
  const errorsSummary = data.errors?.summary || {};
  const auditSummary = data.audit?.summary || {};
  const feedbackSummary = data.feedbacks?.summary || {};
  const healthDependencies = data.health?.dependencies || {};

  const healthDistribution = useMemo(() => {
    const databaseReady = Boolean(healthDependencies.database?.reachable);
    const checks = [
      data.health?.status === 'ok',
      databaseReady,
      Boolean(healthDependencies.openaiConfigured),
      Boolean(healthDependencies.clerkConfigured),
      Boolean(healthDependencies.stripeConfigured),
      Boolean(healthDependencies.pdfGeneratorAvailable),
    ];
    const ready = checks.filter(Boolean).length;
    return [
      { label: 'Operacionais', value: ready, color: '#64e6a6' },
      { label: 'Atenções', value: checks.length - ready, color: '#ff9f5a' },
    ];
  }, [data.health?.status, healthDependencies]);

  const growthData = (data.users?.growth || []).map((item) => ({
    label: item.label,
    value: item.count,
  }));

  const financialData = [
    { label: 'Receita do mês', value: billingSummary.revenueMonthCents || 0, color: '#64e6a6' },
    { label: 'Receita recorrente', value: billingSummary.mrrCents || 0, color: '#f4c95d' },
    { label: 'Valor pendente', value: billingSummary.pendingAmountCents || 0, color: '#ff657f' },
  ];

  const errorDistribution = [
    { label: 'Ativos', value: errorsSummary.activeGroups || 0, color: '#ff657f' },
    { label: 'Estabilizados', value: errorsSummary.stableGroups || 0, color: '#f4c95d' },
    { label: 'Resolvidos', value: errorsSummary.resolvedGroups || 0, color: '#64e6a6' },
  ];

  const auditData = [
    { label: 'Plano', value: auditSummary.planChanges || 0 },
    { label: 'Pagamento aprovado', value: auditSummary.paymentsApproved || 0 },
    { label: 'Pagamento recusado', value: auditSummary.paymentsFailed || 0 },
    { label: 'Cancelamentos', value: auditSummary.subscriptionsCanceled || 0 },
    { label: 'Créditos adicionados', value: auditSummary.creditsAdded || 0 },
    { label: 'Créditos consumidos', value: auditSummary.creditsConsumed || 0 },
    { label: 'PDFs', value: auditSummary.pdfsDelivered || 0 },
  ];

  const feedbackDistribution = [
    { label: 'Sugestões', value: feedbackSummary.suggestions || 0, color: '#3fd7ff' },
    { label: 'Problemas', value: feedbackSummary.problems || 0, color: '#ff657f' },
    { label: 'Elogios', value: feedbackSummary.praises || 0, color: '#f4c95d' },
  ];

  function refresh(event) {
    event.currentTarget.blur();
    loadOverview();
  }

  return (
    <section className="domnai-admin-overview-view" aria-label="Visão geral administrativa">
      <header className="domnai-admin-premium-heading">
        <div>
          <span className="domnai-premium-live"><i />Central oficial · dados reais</span>
          <small>{generatedAt ? `Última atualização: ${formatDate(generatedAt)}` : 'Conectando os módulos...'}</small>
        </div>
        <button type="button" onClick={refresh} disabled={status === 'loading'}>
          {status === 'loading' ? 'Atualizando...' : 'Atualizar'}
        </button>
      </header>

      <section className="domnai-overview-hero">
        <div>
          <span>Monitor operacional DomnAI</span>
          <h1>{data.health?.statusLabel || (status === 'ready' ? 'Monitoramento ativo' : 'Sincronizando')}</h1>
          <p>Usuários, faturamento, falhas, auditoria, feedbacks e serviços acompanhados em uma única central.</p>
        </div>
        <div className="domnai-overview-orbit" aria-hidden="true">
          <i /><i /><i />
          <strong>{healthDistribution[0].value}/6</strong>
          <span>serviços</span>
        </div>
      </section>

      {warning ? <div className="domnai-premium-warning">{warning}</div> : null}

      <div className="domnai-overview-metrics">
        <article data-tone="cyan"><span>Usuários</span><strong>{formatNumber(usersSummary.totalUsers)}</strong><small>{formatNumber(usersSummary.activeLast7Days)} ativos em 7 dias</small></article>
        <article data-tone="green"><span>Receita do mês</span><strong>{formatMoney(billingSummary.revenueMonthCents)}</strong><small>{formatMoney(billingSummary.mrrCents)} recorrentes</small></article>
        <article data-tone="red"><span>Erros ativos</span><strong>{formatNumber(errorsSummary.activeGroups)}</strong><small>{formatNumber(errorsSummary.affectedModules)} módulos afetados</small></article>
        <article data-tone="purple"><span>Eventos auditados</span><strong>{formatNumber(data.audit?.total)}</strong><small>ações financeiras e PDFs</small></article>
        <article data-tone="gold"><span>Avaliação</span><strong>{Number(feedbackSummary.average || 0).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</strong><small>{formatNumber(feedbackSummary.total)} feedbacks</small></article>
        <article data-tone="green"><span>Saúde geral</span><strong>{data.health?.statusLabel || 'Verificando'}</strong><small>{formatNumber(data.health?.serverCheckMs)} ms internos</small></article>
      </div>

      <div className="domnai-premium-chart-grid overview-grid">
        <InteractiveLineChart
          title="Crescimento de usuários"
          subtitle="Últimos 30 dias"
          data={growthData}
          primaryLabel="Novos usuários"
        />
        <InteractiveBarChart
          title="Pulso financeiro"
          subtitle="Valores atuais"
          data={financialData}
          valueFormatter={formatMoney}
        />
        <InteractiveDonutChart
          title="Saúde dos serviços"
          subtitle="Verificação atual"
          data={healthDistribution}
          centerLabel="Serviços"
        />
        <InteractiveDonutChart
          title="Estado dos erros"
          subtitle="Grupos monitorados"
          data={errorDistribution}
          centerLabel="Grupos"
        />
        <InteractiveBarChart
          title="Auditoria em tempo real"
          subtitle="Ações registradas"
          data={auditData}
        />
        <InteractiveDonutChart
          title="Voz dos usuários"
          subtitle="Feedbacks recebidos"
          data={feedbackDistribution}
          centerLabel="Feedbacks"
        />
      </div>
    </section>
  );
}
