import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
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
