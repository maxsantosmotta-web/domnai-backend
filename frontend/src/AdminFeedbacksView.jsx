import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import './admin-feedbacks-view.css';
import './admin-feedbacks-refine.css';

const FILTERS = [
  { value: 'all', label: 'Todos' },
  { value: 'suggestion', label: 'Sugestões' },
  { value: 'problem', label: 'Problemas' },
  { value: 'praise', label: 'Elogios' },
];

const EMPTY_SUMMARY = {
  total: 0,
  suggestions: 0,
  problems: 0,
  praises: 0,
  average: 0,
};

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
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [filter, setFilter] = useState('all');
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState('');
  const [deletingAll, setDeletingAll] = useState(false);

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

      const nextItems = Array.isArray(payload.items) ? payload.items : [];
      setItems(nextItems);
      setSummary({
        total: Number(payload.summary?.total) || 0,
        suggestions: Number(payload.summary?.suggestions) || 0,
        problems: Number(payload.summary?.problems) || 0,
        praises: Number(payload.summary?.praises) || 0,
        average: Number(payload.summary?.average) || 0,
      });
      setStatus('ready');
    } catch (loadError) {
      setError(loadError?.message || 'Não foi possível carregar os feedbacks.');
      setStatus('error');
    }
  }, [getToken]);

  useEffect(() => {
    loadFeedbacks();
  }, [loadFeedbacks]);

  const visibleItems = useMemo(
    () => (filter === 'all' ? items : items.filter((item) => item.category === filter)),
    [filter, items],
  );

  async function deleteFeedback(item) {
    const confirmed = window.confirm(
      'Excluir este feedback da lista administrativa? Os números do relatório serão preservados.',
    );
    if (!confirmed) return;

    setDeletingId(item.id);
    try {
      const token = await getToken();
      const response = await fetch(`/api/feedback/admin/${encodeURIComponent(item.id)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível excluir o feedback.');
      setItems((current) => current.filter((currentItem) => currentItem.id !== item.id));
    } catch (deleteError) {
      window.alert(deleteError?.message || 'Não foi possível excluir o feedback.');
    } finally {
      setDeletingId('');
    }
  }

  async function deleteAllFeedbacks() {
    if (items.length === 0) return;
    const confirmed = window.confirm(
      'Excluir todos os feedbacks da lista administrativa? Os números do relatório serão preservados.',
    );
    if (!confirmed) return;

    setDeletingAll(true);
    try {
      const token = await getToken();
      const response = await fetch('/api/feedback/admin', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || 'Não foi possível excluir os feedbacks.');
      setItems([]);
    } catch (deleteError) {
      window.alert(deleteError?.message || 'Não foi possível excluir os feedbacks.');
    } finally {
      setDeletingAll(false);
    }
  }

  function refreshFeedbacks(event) {
    event.currentTarget.blur();
    loadFeedbacks();
  }

  return (
    <section className="domnai-admin-feedbacks-view" aria-label="Feedbacks recebidos">
      <header className="domnai-admin-feedbacks-heading">
        <div className="domnai-admin-feedbacks-actions">
          <button type="button" onClick={refreshFeedbacks} disabled={status === 'loading'}>
            {status === 'loading' ? 'Atualizando...' : 'Atualizar'}
          </button>
        </div>
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

      <div className="domnai-admin-feedback-list-actions">
        <button
          type="button"
          className="delete-all"
          onClick={deleteAllFeedbacks}
          disabled={status === 'loading' || deletingAll || items.length === 0}
        >
          {deletingAll ? 'Excluindo...' : 'Excluir todos'}
        </button>
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
        <div className="domnai-admin-feedbacks-state compact">
          <strong>Nenhum feedback na lista</strong>
          <p>Os indicadores históricos permanecem preservados.</p>
        </div>
      ) : null}

      {status === 'ready' && visibleItems.length > 0 ? (
        <div className="domnai-admin-feedbacks-list" aria-label="Lista de feedbacks recebidos">
          {visibleItems.map((item) => (
            <article className={`domnai-admin-feedback-item ${item.category || ''}`} key={item.id}>
              <div className="domnai-admin-feedback-item-top">
                <div>
                  <span className="category">{item.categoryLabel || 'Feedback'}</span>
                  <span className="status">{item.statusLabel || 'Recebido'}</span>
                </div>
                <div className="domnai-admin-feedback-item-actions">
                  <time dateTime={item.createdAt}>{formatDate(item.createdAt)}</time>
                  <button
                    type="button"
                    onClick={() => deleteFeedback(item)}
                    disabled={deletingId === item.id || deletingAll}
                  >
                    {deletingId === item.id ? 'Excluindo...' : 'Excluir'}
                  </button>
                </div>
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
