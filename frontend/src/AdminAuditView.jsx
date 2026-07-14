import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import './admin-audit-view.css';

const EMPTY_SUMMARY = {
  total: 0,
  plans: 0,
  payments: 0,
  credits: 0,
  pdfs: 0,
};

const CATEGORY_OPTIONS = [
  { value: 'all', label: 'Todas as ações' },
  { value: 'plan', label: 'Planos' },
  { value: 'payment', label: 'Pagamentos' },
  { value: 'credits', label: 'Créditos' },
  { value: 'pdf', label: 'PDFs concluídos' },
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
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [total, setTotal] = useState(0);
  const [generatedAt, setGeneratedAt] = useState('');
  const [category, setCategory] = useState('all');
  const [visibleLimit, setVisibleLimit] = useState(10);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  const loadAudit = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setStatus('loading');
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Não foi possível validar a sessão administrativa.');
      const params = new URLSearchParams({ category, limit: String(visibleLimit) });
      const response = await fetch(`/api/admin/audit?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      const payload = await readResponse(response);
      if (!response.ok) {
        throw new Error(payload.detail || `Falha ao carregar a auditoria (${response.status}).`);
      }
      setItems(Array.isArray(payload.items) ? payload.items : []);
      setSummary({ ...EMPTY_SUMMARY, ...(payload.summary || {}) });
      setTotal(Number(payload.total || 0));
      setGeneratedAt(payload.generatedAt || new Date().toISOString());
      setStatus('ready');
    } catch (loadError) {
      if (!silent) {
        setError(loadError?.message || 'Não foi possível carregar a auditoria.');
        setStatus('error');
      }
    }
  }, [category, getToken, visibleLimit]);

  useEffect(() => {
    loadAudit();
    const interval = window.setInterval(() => loadAudit({ silent: true }), 15000);
    return () => window.clearInterval(interval);
  }, [loadAudit]);

  function handleRefresh(event) {
    event.currentTarget.blur();
    loadAudit();
  }

  function handleCategoryChange(event) {
    setCategory(event.target.value);
    setVisibleLimit(10);
  }

  function handleShowMore(event) {
    event.currentTarget.blur();
    setVisibleLimit((current) => Math.min(current + 10, 100));
  }

  function handleShowLess(event) {
    event.currentTarget.blur();
    setVisibleLimit(10);
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
        <article><span>Total de eventos</span><strong>{formatNumber(summary.total)}</strong></article>
        <article><span>Planos</span><strong>{formatNumber(summary.plans)}</strong></article>
        <article><span>Pagamentos</span><strong>{formatNumber(summary.payments)}</strong></article>
        <article><span>Créditos</span><strong>{formatNumber(summary.credits)}</strong></article>
        <article><span>PDFs concluídos</span><strong>{formatNumber(summary.pdfs)}</strong></article>
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

      {status === 'ready' ? (
        <>
          <div className="domnai-admin-audit-toolbar">
            <label>
              <span>Tipo de ação</span>
              <select value={category} onChange={handleCategoryChange}>
                {CATEGORY_OPTIONS.map((option) => (
                  <option value={option.value} key={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <div className="audit-result-count">
              <span>Registros encontrados</span>
              <strong>{formatNumber(total)}</strong>
            </div>
          </div>

          {items.length === 0 ? (
            <div className="domnai-admin-audit-state compact">
              <strong>Nenhum evento registrado</strong>
              <p>Planos, pagamentos, créditos e PDFs concluídos aparecerão aqui automaticamente.</p>
            </div>
          ) : (
            <section className="domnai-admin-audit-list-card">
              <header>
                <div>
                  <span>Histórico auditável</span>
                  <strong>Somente ações que alteram plano, pagamento, créditos ou entregam PDF</strong>
                </div>
                <small>{formatNumber(items.length)} de {formatNumber(total)}</small>
              </header>

              <div className="domnai-admin-audit-list">
                {items.map((item) => (
                  <article className={`audit-row ${item.result}`} key={item.id}>
                    <div className="audit-category">
                      <span>{item.categoryLabel}</span>
                      <strong>{item.module}</strong>
                    </div>
                    <div className="audit-user">
                      <span>Usuário</span>
                      <strong>{item.userName}</strong>
                    </div>
                    <div className="audit-action">
                      <strong>{item.actionLabel}</strong>
                      <p>{item.description}</p>
                    </div>
                    <div className="audit-result">
                      <span className={item.result}>{item.resultLabel}</span>
                    </div>
                    <div className="audit-date">
                      <span>Data e horário</span>
                      <strong>{formatDate(item.createdAt)}</strong>
                    </div>
                  </article>
                ))}
              </div>

              {total > 10 ? (
                <div className="audit-list-actions">
                  {items.length < total && visibleLimit < 100 ? (
                    <button type="button" onClick={handleShowMore}>Mostrar mais</button>
                  ) : null}
                  {visibleLimit > 10 ? (
                    <button type="button" onClick={handleShowLess}>Mostrar menos</button>
                  ) : null}
                </div>
              ) : null}
            </section>
          )}
        </>
      ) : null}
    </section>
  );
}
