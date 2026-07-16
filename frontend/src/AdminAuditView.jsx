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

const AUDIT_COUNTER_LABELS = {
  planChanges: 'Plano escolhido ou alterado',
  paymentsApproved: 'Pagamento aprovado',
  paymentsFailed: 'Pagamento recusado',
  subscriptionsCanceled: 'Assinatura cancelada',
  creditsAdded: 'Créditos adicionados',
  creditsConsumed: 'Créditos consumidos',
  pdfsDelivered: 'PDF concluído pelo chat',
  spreadsheetsDelivered: 'Planilha concluída pelo chat',
  conversationsCompleted: 'Conversas/Operações concluídas',
};

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

  const auditCounters = useMemo(() => Object.entries(summary).map(([key, value]) => ({
    key,
    label: AUDIT_COUNTER_LABELS[key] || key,
    value: Number(value || 0),
  })), [summary]);

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
        {auditCounters.map((counter) => (
          <article key={counter.key}>
            <span>{counter.label}</span>
            <strong>{formatNumber(counter.value)}</strong>
          </article>
        ))}
      </div>

      {status === 'ready' ? (
        <section className="domnai-premium-chart-grid audit-premium-charts domnai-admin-audit-charts" aria-label="Gráficos da auditoria">
          <InteractiveBarChart
            title="Auditoria em tempo real"
            subtitle="Ações registradas"
            data={auditCounters}
          />
          <InteractiveDonutChart
            title="Distribuição dos contadores"
            subtitle="Balanço atual"
            data={auditCounters}
            centerLabel="Ações"
          />
        </section>
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
