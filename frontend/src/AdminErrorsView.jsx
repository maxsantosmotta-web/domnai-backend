import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import './admin-errors-view.css';

const EMPTY_SUMMARY = {
  activeGroups: 0,
  stableGroups: 0,
  resolvedGroups: 0,
  criticalGroups: 0,
  warningGroups: 0,
  affectedModules: 0,
  totalOccurrences: 0,
  totalGroups: 0,
};

const SEVERITY_FILTERS = [
  { value: 'all', label: 'Todas as gravidades' },
  { value: 'critical', label: 'Crítico' },
  { value: 'error', label: 'Erro' },
  { value: 'warning', label: 'Alerta' },
];

const STATUS_FILTERS = [
  { value: 'all', label: 'Todos os status' },
  { value: 'active', label: 'Ativo' },
  { value: 'stable', label: 'Estabilizado' },
  { value: 'resolved', label: 'Resolvido' },
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

function exportErrorsCsv(items) {
  const header = [
    'Módulo',
    'Gravidade',
    'Status',
    'Erro ou alerta',
    'Detalhes',
    'Quantidade',
    'Primeira ocorrência',
    'Última ocorrência',
    'Rota',
  ];
  const rows = items.map((item) => [
    item.module,
    item.severityLabel,
    item.statusLabel,
    item.title,
    item.message,
    item.occurrences,
    formatDate(item.firstSeenAt),
    formatDate(item.lastSeenAt),
    item.path,
  ]);
  const escape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
  const csv = [header, ...rows].map((row) => row.map(escape).join(';')).join('\n');
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `domnai-erros-alertas-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function AdminErrorsView() {
  const { getToken } = useAuth();
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [generatedAt, setGeneratedAt] = useState('');
  const [moduleFilter, setModuleFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showAll, setShowAll] = useState(false);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  const loadErrors = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setStatus('loading');
    setError('');
    try {
      const token = await getToken();
      if (!token) throw new Error('Não foi possível validar a sessão administrativa.');
      const response = await fetch('/api/admin/errors?limit=2000', {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      const payload = await readResponse(response);
      if (!response.ok) {
        throw new Error(payload.detail || `Falha ao carregar erros e alertas (${response.status}).`);
      }
      setItems(Array.isArray(payload.items) ? payload.items : []);
      setSummary({ ...EMPTY_SUMMARY, ...(payload.summary || {}) });
      setGeneratedAt(payload.generatedAt || new Date().toISOString());
      setStatus('ready');
    } catch (loadError) {
      if (!silent) {
        setError(loadError?.message || 'Não foi possível carregar erros e alertas.');
        setStatus('error');
      }
    }
  }, [getToken]);

  useEffect(() => {
    loadErrors();
    const interval = window.setInterval(() => loadErrors({ silent: true }), 15000);
    return () => window.clearInterval(interval);
  }, [loadErrors]);

  const affectedModules = useMemo(() => (
    Array.from(new Set(
      items
        .filter((item) => item.status !== 'resolved')
        .map((item) => String(item.module || '').trim())
        .filter(Boolean),
    )).sort((a, b) => a.localeCompare(b, 'pt-BR'))
  ), [items]);

  useEffect(() => {
    if (moduleFilter !== 'all' && !affectedModules.includes(moduleFilter)) {
      setModuleFilter('all');
    }
  }, [affectedModules, moduleFilter]);

  const filteredItems = useMemo(() => items.filter((item) => {
    const matchesModule = moduleFilter === 'all' || item.module === moduleFilter;
    const matchesSeverity = severityFilter === 'all' || item.severity === severityFilter;
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    return matchesModule && matchesSeverity && matchesStatus;
  }), [items, moduleFilter, severityFilter, statusFilter]);

  const visibleItems = showAll ? filteredItems : filteredItems.slice(0, 8);

  function handleRefresh(event) {
    event.currentTarget.blur();
    loadErrors();
  }

  function handleExport(event) {
    event.currentTarget.blur();
    exportErrorsCsv(filteredItems);
  }

  function handleShowAll(event) {
    event.currentTarget.blur();
    setShowAll((current) => !current);
  }

  function selectModule(event, moduleName) {
    event.currentTarget.blur();
    setModuleFilter(moduleName);
    setShowAll(false);
  }

  return (
    <section className="domnai-admin-errors-view" aria-label="Erros e alertas administrativos">
      <header className="domnai-admin-errors-heading">
        <div>
          <span className="errors-live-indicator"><i />Monitoramento real · atualização automática</span>
          <small>{generatedAt ? `Última atualização: ${formatDate(generatedAt)}` : 'Conectando dados...'}</small>
        </div>
        <div className="errors-heading-actions">
          <button type="button" onClick={handleExport} disabled={status !== 'ready' || filteredItems.length === 0}>Exportar CSV</button>
          <button type="button" onClick={handleRefresh} disabled={status === 'loading'}>{status === 'loading' ? 'Atualizando...' : 'Atualizar'}</button>
        </div>
      </header>

      <div className="domnai-admin-errors-summary" aria-label="Resumo de erros e alertas">
        <article><span>Erros ativos</span><strong>{formatNumber(summary.activeGroups)}</strong></article>
        <article><span>Estabilizados</span><strong>{formatNumber(summary.stableGroups)}</strong></article>
        <article><span>Módulos afetados</span><strong>{formatNumber(summary.affectedModules)}</strong></article>
        <article><span>Ocorrências acumuladas</span><strong>{formatNumber(summary.totalOccurrences)}</strong></article>
        <article><span>Críticos</span><strong>{formatNumber(summary.criticalGroups)}</strong></article>
      </div>

      {status === 'loading' ? (
        <div className="domnai-admin-errors-state"><span className="errors-spinner" />Carregando monitoramento real...</div>
      ) : null}

      {status === 'error' ? (
        <div className="domnai-admin-errors-state error">
          <strong>Não foi possível carregar Erros e alertas.</strong>
          <p>{error}</p>
          <button type="button" onClick={() => loadErrors()}>Tentar novamente</button>
        </div>
      ) : null}

      {status === 'ready' ? (
        <>
          <section className="domnai-admin-errors-modules" aria-label="Módulos com erro">
            <header>
              <span>Módulos com erro</span>
              <strong>{affectedModules.length > 0 ? 'Selecione o módulo para ver os detalhes' : 'Nenhum módulo com falha'}</strong>
            </header>
            {affectedModules.length > 0 ? (
              <div className="errors-module-buttons">
                <button
                  type="button"
                  className={moduleFilter === 'all' ? 'selected' : ''}
                  onClick={(event) => selectModule(event, 'all')}
                >
                  Todos os módulos
                </button>
                {affectedModules.map((moduleName) => (
                  <button
                    type="button"
                    className={moduleFilter === moduleName ? 'selected' : ''}
                    onClick={(event) => selectModule(event, moduleName)}
                    key={moduleName}
                  >
                    {moduleName}
                  </button>
                ))}
              </div>
            ) : (
              <p>Quando surgir uma falha, o nome do módulo aparecerá aqui automaticamente.</p>
            )}
          </section>

          <div className="domnai-admin-errors-toolbar">
            <label>
              <span>Gravidade</span>
              <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
                {SEVERITY_FILTERS.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
              </select>
            </label>
            <label>
              <span>Status</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                {STATUS_FILTERS.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
              </select>
            </label>
            <div className="errors-result-count"><span>Grupos</span><strong>{formatNumber(filteredItems.length)}</strong></div>
          </div>

          {filteredItems.length === 0 ? (
            <div className="domnai-admin-errors-state compact">
              <strong>Nenhum erro ou alerta registrado</strong>
              <p>As novas ocorrências serão agrupadas automaticamente por módulo e tipo.</p>
            </div>
          ) : (
            <section className="domnai-admin-errors-list-card">
              <header>
                <div><span>Ocorrências agrupadas</span><strong>Módulo, erro, quantidade e estado atual</strong></div>
                <small>{formatNumber(visibleItems.length)} de {formatNumber(filteredItems.length)}</small>
              </header>

              <div className="domnai-admin-errors-list">
                {visibleItems.map((item) => (
                  <article className={`error-group ${item.severity} ${item.status}`} key={item.id}>
                    <div className="error-group-module">
                      <span>{item.module}</span>
                      <strong>{item.severityLabel}</strong>
                    </div>
                    <div className="error-group-copy">
                      <strong>{item.title}</strong>
                      <p>{item.message}</p>
                      {item.path ? <small>{item.method ? `${item.method} · ` : ''}{item.path}</small> : null}
                    </div>
                    <div className="error-group-count">
                      <span>Quantidade</span>
                      <strong>{formatNumber(item.occurrences)}</strong>
                    </div>
                    <div className="error-group-last">
                      <span>Última ocorrência</span>
                      <strong>{formatDate(item.lastSeenAt)}</strong>
                    </div>
                    <div className="error-group-status">
                      <span className={item.status}>{item.statusLabel}</span>
                    </div>
                  </article>
                ))}
              </div>

              {filteredItems.length > 8 ? (
                <div className="errors-show-all-wrap">
                  <button type="button" onClick={handleShowAll}>{showAll ? 'Mostrar menos' : `Mostrar tudo (${formatNumber(filteredItems.length)})`}</button>
                </div>
              ) : null}
            </section>
          )}
        </>
      ) : null}
    </section>
  );
}
