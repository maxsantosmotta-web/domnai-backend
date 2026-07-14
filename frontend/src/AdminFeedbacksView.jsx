import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import './admin-feedbacks-view.css';

const FILTERS = [
  { value: 'all', label: 'Todos' },
  { value: 'suggestion', label: 'Sugestões' },
  { value: 'problem', label: 'Problemas' },
  { value: 'praise', label: 'Elogios' },
];

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function Stars({ rating }) {
  const normalized = Math.max(0, Math.min(5, Number(rating) || 0));
  return (
    <span className="domnai-admin-feedback-stars" aria-label={`${normalized} de 5 estrelas`}>
      {[1, 2, 3, 4, 5].map((value) => (
        <span className={value <= normalized ? 'filled' : ''} key={value}>★</span>
      ))}
    </span>
  );
}

export default function AdminFeedbacksView() {
  const { getToken } = useAuth();
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState('all');
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  const loadFeedbacks = useCallback(async () => {
    setStatus('loading');
    setError('');

    try {
      const token = await getToken();
      const response = await fetch('/api/feedback/admin?limit=200', {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível carregar os feedbacks.');
      setItems(Array.isArray(payload.items) ? payload.items : []);
      setStatus('ready');
    } catch (loadError) {
      setError(loadError?.message || 'Não foi possível carregar os feedbacks.');
      setStatus('error');
    }
  }, [getToken]);

  useEffect(() => {
    loadFeedbacks();
  }, [loadFeedbacks]);

  const summary = useMemo(() => {
    const total = items.length;
    const suggestions = items.filter((item) => item.category === 'suggestion').length;
    const problems = items.filter((item) => item.category === 'problem').length;
    const praises = items.filter((item) => item.category === 'praise').length;
    const average = total
      ? items.reduce((sum, item) => sum + (Number(item.rating) || 0), 0) / total
      : 0;

    return { total, suggestions, problems, praises, average };
  }, [items]);

  const visibleItems = useMemo(
    () => (filter === 'all' ? items : items.filter((item) => item.category === filter)),
    [filter, items],
  );

  return (
    <section className="domnai-admin-feedbacks-view" aria-labelledby="admin-feedbacks-title">
      <header className="domnai-admin-feedbacks-heading">
        <div>
          <h2 id="admin-feedbacks-title">Feedbacks recebidos</h2>
          <p>Acompanhe sugestões, problemas e elogios enviados pelos usuários.</p>
        </div>
        <button type="button" onClick={loadFeedbacks} disabled={status === 'loading'}>
          {status === 'loading' ? 'Atualizando...' : 'Atualizar'}
        </button>
      </header>

      <div className="domnai-admin-feedbacks-summary" aria-label="Resumo dos feedbacks">
        <article><span>Total</span><strong>{summary.total}</strong></article>
        <article><span>Sugestões</span><strong>{summary.suggestions}</strong></article>
        <article><span>Problemas</span><strong>{summary.problems}</strong></article>
        <article><span>Elogios</span><strong>{summary.praises}</strong></article>
        <article><span>Média</span><strong>{summary.average.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</strong></article>
      </div>

      <div className="domnai-admin-feedbacks-toolbar" role="group" aria-label="Filtrar feedbacks">
        {FILTERS.map((item) => (
          <button
            type="button"
            className={filter === item.value ? 'selected' : ''}
            aria-pressed={filter === item.value}
            onClick={() => setFilter(item.value)}
            key={item.value}
          >
            {item.label}
          </button>
        ))}
      </div>

      {status === 'loading' ? (
        <div className="domnai-admin-feedbacks-state"><span className="spinner" />Carregando feedbacks...</div>
      ) : null}

      {status === 'error' ? (
        <div className="domnai-admin-feedbacks-state error">
          <strong>Não foi possível carregar.</strong>
          <p>{error}</p>
          <button type="button" onClick={loadFeedbacks}>Tentar novamente</button>
        </div>
      ) : null}

      {status === 'ready' && visibleItems.length === 0 ? (
        <div className="domnai-admin-feedbacks-state">
          <strong>Nenhum feedback encontrado</strong>
          <p>Os novos registros aparecerão aqui automaticamente após a atualização.</p>
        </div>
      ) : null}

      {status === 'ready' && visibleItems.length > 0 ? (
        <div className="domnai-admin-feedbacks-list">
          {visibleItems.map((item) => (
            <article className={`domnai-admin-feedback-item ${item.category || ''}`} key={item.id}>
              <div className="domnai-admin-feedback-item-top">
                <div>
                  <span className="category">{item.categoryLabel || 'Feedback'}</span>
                  <span className="status">{item.statusLabel || 'Recebido'}</span>
                </div>
                <time dateTime={item.createdAt}>{formatDate(item.createdAt)}</time>
              </div>

              <div className="domnai-admin-feedback-user">
                <strong>{item.userName || 'Usuário DomnAI'}</strong>
                <Stars rating={item.rating} />
              </div>

              <h3>{item.title || 'Feedback'}</h3>
              <p>{item.message}</p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
