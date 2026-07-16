import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { InteractiveBarChart, InteractiveDonutChart } from './AdminPremiumCharts';
import './admin-audit-view.css';

const EMPTY_SUMMARY = {
  planChanges: 0,
  paymentsApproved: 0,
  paymentsFailed: 0,
  subscriptionsCanceled: 0,
  creditsAdded: 0,
  creditsConsumed: 0,
  pdfsDelivered: 0,
  spreadsheetsDelivered: 0,
  conversationsCompleted: 0,
};

const AUDIT_COUNTERS = [
  ['planChanges', 'Planos'],
  ['paymentsApproved', 'Pagamentos aprovados'],
  ['paymentsFailed', 'Pagamentos recusados'],
  ['subscriptionsCanceled', 'Cancelamentos'],
  ['creditsAdded', 'Créditos adicionados'],
  ['creditsConsumed', 'Créditos consumidos'],
  ['pdfsDelivered', 'PDFs concluídos'],
  ['spreadsheetsDelivered', 'Planilhas concluídas'],
  ['conversationsCompleted', 'Conversas/Operações'],
];

function formatNumber(value) {
  return Number(value || 0).toLocaleString('pt-BR');
}

function formatDate(value) {
  if (!value) return 'Sem registro';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Sem registro';
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
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

export default function AdminAuditView() {
  const { getToken } = useAuth();
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [generatedAt, setGeneratedAt] = useState('');
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  const auditCounters = useMemo(() => AUDIT_COUNTERS.map(([key, label]) => ({
    key,
    label,
    value: Number(summary[key] || 0),
  })), [summary]);

  const completedActions = useMemo(() => Number(summary.planChanges || 0)
    + Number(summary.paymentsApproved || 0)
    + Number(summary.creditsAdded || 0)
    + Number(summary.creditsConsumed || 0)
    + Number(summary.pdfsDelivered || 0)
    + Number(summary.spreadsheetsDelivered || 0)
    + Number(summary.conversationsCompleted || 0), [summary]);

  const actionBalance = useMemo(() => ([
    { label: 'Concluídas', value: completedActions, color: '#64e6a6' },
    { label: 'Recusadas', value: Number(summary.paymentsFailed || 0), color: '#ff657f' },
    { label: 'Canceladas', value: Number(summary.subscriptionsCanceled || 0), color: '#ff9f5a' },
  ]), [completedActions, summary.paymentsFailed, summary.subscriptionsCanceled]);

  const loadAudit = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setStatus('loading');
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Não foi possível validar a sessão administrativa.');
      const response = await fetch('/api/admin/audit', {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      const payload = await readResponse(response);
      if (!response.ok) {
        throw new Error(payload.detail || `Falha ao carregar a auditoria (${response.status}).`);
      }
      setSummary({ ...EMPTY_SUMMARY, ...(payload.summary || {}) });
      setGeneratedAt(payload.generatedAt || new Date().toISOString());
      setStatus('ready');
    } catch (loadError) {
      if (!silent) {
        setError(loadError?.message || 'Não foi possível carregar a auditoria.');
        setStatus('error');
      }
    }
  }, [getToken]);

  useEffect(() => {
    loadAudit();
    const interval = window.setInterval(() => loadAudit({ silent: true }), 15000);
    return () => window.clearInterval(interval);
  }, [loadAudit]);

  function handleRefresh(event) {
    event.currentTarget.blur();
    loadAudit();
  }

  return (
    <section className="domnai-admin-audit-view" aria-label="Auditoria administrativa">
      <header className="domnai-admin-audit-heading">
        <div>
          <span className="audit-live-indicator"><i />Auditoria real · atualização automática</span>
          <small>{generatedAt ? `Última atualização: ${formatDate(generatedAt)}` : 'Conectando dados...'}</small>
        </div>
        <button type="button" onClick={handleRefresh} disabled={status === 'loading'}>
          {status === 'loading' ? 'Atualizando...' : 'Atualizar'}
        </button>
      </header>

      <div className="domnai-admin-audit-summary" aria-label="Resumo da auditoria">
        <article><span>Plano escolhido ou alterado</span><strong>{formatNumber(summary.planChanges)}</strong></article>
        <article><span>Pagamento aprovado</span><strong>{formatNumber(summary.paymentsApproved)}</strong></article>
        <article><span>Pagamento recusado</span><strong>{formatNumber(summary.paymentsFailed)}</strong></article>
        <article><span>Assinatura cancelada</span><strong>{formatNumber(summary.subscriptionsCanceled)}</strong></article>
        <article><span>Créditos adicionados</span><strong>{formatNumber(summary.creditsAdded)}</strong></article>
        <article><span>Créditos consumidos</span><strong>{formatNumber(summary.creditsConsumed)}</strong></article>
        <article><span>PDF concluído pelo chat</span><strong>{formatNumber(summary.pdfsDelivered)}</strong></article>
        <article><span>Planilha concluída pelo chat</span><strong>{formatNumber(summary.spreadsheetsDelivered)}</strong></article>
        <article><span>Conversas/Operações concluídas</span><strong>{formatNumber(summary.conversationsCompleted)}</strong></article>
      </div>

      {status === 'ready' ? (
        <div className="domnai-premium-chart-grid audit-premium-charts">
          <InteractiveBarChart
            title="Ações auditadas"
            subtitle="Contadores funcionais"
            data={auditCounters}
          />
          <InteractiveDonutChart
            title="Balanço das ações"
            subtitle="Concluídas e atenções"
            data={actionBalance}
            centerLabel="Eventos"
          />
        </div>
      ) : null}

      {status === 'loading' ? (
        <div className="domnai-admin-audit-state"><span className="audit-spinner" />Carregando auditoria...</div>
      ) : null}

      {status === 'error' ? (
        <div className="domnai-admin-audit-state error">
          <strong>Não foi possível carregar a Auditoria.</strong>
          <p>{error}</p>
          <button type="button" onClick={() => loadAudit()}>Tentar novamente</button>
        </div>
      ) : null}
    </section>
  );
}
