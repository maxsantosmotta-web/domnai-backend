import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/clerk-react';
import './admin-users-view.css';

const EMPTY_SUMMARY = {
  totalUsers: 0,
  newThisWeek: 0,
  newThisMonth: 0,
  profileCompleted: 0,
  premiumUsers: 0,
  freeUsers: 0,
  unselectedUsers: 0,
  adminUsers: 0,
  activeLast7Days: 0,
  totalCredits: 0,
};

const PLAN_FILTERS = [
  { value: 'all', label: 'Todos os planos' },
  { value: 'free', label: 'Plano Free' },
  { value: 'premium', label: 'Plano Premium' },
  { value: 'unselected', label: 'Sem plano' },
  { value: 'admin', label: 'Administrativo' },
];

const ROLE_FILTERS = [
  { value: 'all', label: 'Todas as funções' },
  { value: 'user', label: 'Usuário' },
  { value: 'admin', label: 'Admin' },
];

function formatNumber(value) {
  return Number(value || 0).toLocaleString('pt-BR');
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

function GrowthChart({ points }) {
  const safePoints = Array.isArray(points) ? points : [];
  const width = 760;
  const height = 220;
  const padding = { top: 20, right: 20, bottom: 38, left: 34 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(1, ...safePoints.map((item) => Number(item.count) || 0));
  const divisor = Math.max(1, safePoints.length - 1);

  const coordinates = safePoints.map((item, index) => {
    const value = Number(item.count) || 0;
    return {
      ...item,
      x: padding.left + (index / divisor) * innerWidth,
      y: padding.top + innerHeight - (value / maxValue) * innerHeight,
      value,
    };
  });

  const line = coordinates
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ');
  const area = coordinates.length
    ? `${line} L ${coordinates[coordinates.length - 1].x} ${padding.top + innerHeight} L ${coordinates[0].x} ${padding.top + innerHeight} Z`
    : '';

  return (
    <div className="domnai-admin-users-chart-wrap">
      <svg
        className="domnai-admin-users-chart"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Novos usuários nos últimos 30 dias"
      >
        {[0, 0.5, 1].map((step) => {
          const y = padding.top + innerHeight - (step * innerHeight);
          return (
            <g key={step}>
              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} className="grid-line" />
              <text x={padding.left - 8} y={y + 4} textAnchor="end" className="axis-value">
                {Math.round(maxValue * step)}
              </text>
            </g>
          );
        })}
        {area ? <path d={area} className="area" /> : null}
        {line ? <path d={line} className="line" /> : null}
        {coordinates.map((point, index) => (
          <g key={point.date || index}>
            {(index % 5 === 0 || index === coordinates.length - 1) ? (
              <text x={point.x} y={height - 12} textAnchor="middle" className="axis-label">
                {point.label}
              </text>
            ) : null}
            <circle
              cx={point.x}
              cy={point.y}
              r={point.value > 0 ? 4 : 2.2}
              className={point.value > 0 ? 'point active' : 'point'}
            >
              <title>{`${point.label}: ${point.value} novo(s) usuário(s)`}</title>
            </circle>
          </g>
        ))}
      </svg>
    </div>
  );
}

function PlanDistribution({ items, total }) {
  return (
    <div className="domnai-admin-users-plan-chart" aria-label="Distribuição por plano">
      {(Array.isArray(items) ? items : []).map((item) => {
        const percentage = total > 0
          ? Math.round((Number(item.count || 0) / total) * 100)
          : 0;
        return (
          <div className="plan-row" key={item.key}>
            <div>
              <span>{item.label}</span>
              <strong>{formatNumber(item.count)} · {percentage}%</strong>
            </div>
            <div className="track" aria-hidden="true">
              <span style={{ width: `${percentage}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function exportUsersCsv(users) {
  const header = [
    'Nome',
    'E-mail',
    'Função',
    'Plano',
    'Status da assinatura',
    'Créditos do plano',
    'Créditos extras',
    'Créditos totais',
    'Perfil completo',
    'Status da conta',
    'Cadastro',
    'Última atividade',
  ];

  const rows = users.map((item) => [
    item.name,
    item.email,
    item.roleLabel,
    item.planLabel,
    item.subscriptionStatus,
    item.planCredits,
    item.extraCredits,
    item.totalCredits,
    item.profileCompleted ? 'Sim' : 'Não',
    item.accountStatusLabel,
    formatDate(item.createdAt, true),
    formatDate(item.lastActivityAt, true),
  ]);

  const escape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
  const csv = [header, ...rows].map((row) => row.map(escape).join(';')).join('\n');
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `domnai-usuarios-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
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

export default function AdminUsersView() {
  const { getToken } = useAuth();
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [growth, setGrowth] = useState([]);
  const [planDistribution, setPlanDistribution] = useState([]);
  const [brainInsights, setBrainInsights] = useState([]);
  const [generatedAt, setGeneratedAt] = useState('');
  const [dataWarning, setDataWarning] = useState('');
  const [query, setQuery] = useState('');
  const [planFilter, setPlanFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  const loadUsers = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setStatus('loading');
    setError('');

    try {
      const token = await getToken();
      if (!token) throw new Error('Não foi possível validar a sessão administrativa.');

      const response = await fetch('/api/admin/users?limit=1000', {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      const payload = await readResponse(response);
      if (!response.ok) {
        throw new Error(payload.detail || `Falha ao carregar usuários (${response.status}).`);
      }

      setItems(Array.isArray(payload.items) ? payload.items : []);
      setSummary({ ...EMPTY_SUMMARY, ...(payload.summary || {}) });
      setGrowth(Array.isArray(payload.growth) ? payload.growth : []);
      setPlanDistribution(Array.isArray(payload.planDistribution) ? payload.planDistribution : []);
      setBrainInsights(Array.isArray(payload.brainInsights) ? payload.brainInsights : []);
      setGeneratedAt(payload.generatedAt || new Date().toISOString());
      setDataWarning(String(payload.dataWarning || ''));
      setStatus('ready');
    } catch (loadError) {
      if (!silent) {
        setError(loadError?.message || 'Não foi possível carregar os usuários.');
        setStatus('error');
      }
    }
  }, [getToken]);

  useEffect(() => {
    loadUsers();
    const interval = window.setInterval(() => loadUsers({ silent: true }), 30000);
    return () => window.clearInterval(interval);
  }, [loadUsers]);

  const visibleUsers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return items.filter((item) => {
      const matchesSearch = !normalizedQuery
        || String(item.name || '').toLowerCase().includes(normalizedQuery)
        || String(item.email || '').toLowerCase().includes(normalizedQuery);
      const matchesPlan = planFilter === 'all' || item.plan === planFilter;
      const matchesRole = roleFilter === 'all' || item.role === roleFilter;
      return matchesSearch && matchesPlan && matchesRole;
    });
  }, [items, planFilter, query, roleFilter]);

  function refreshUsers(event) {
    event.currentTarget.blur();
    loadUsers();
  }

  function handleExport(event) {
    event.currentTarget.blur();
    exportUsersCsv(visibleUsers);
  }

  return (
    <section className="domnai-admin-users-view" aria-label="Gestão de usuários">
      <header className="domnai-admin-users-heading">
        <div>
          <span className="live-indicator"><i />Dados reais · atualização automática</span>
          <small>
            {generatedAt
              ? `Última atualização: ${formatDate(generatedAt, true)}`
              : 'Conectando dados...'}
          </small>
        </div>
        <div className="heading-actions">
          <button
            type="button"
            onClick={handleExport}
            disabled={status !== 'ready' || visibleUsers.length === 0}
          >
            Exportar CSV
          </button>
          <button type="button" onClick={refreshUsers} disabled={status === 'loading'}>
            {status === 'loading' ? 'Atualizando...' : 'Atualizar'}
          </button>
        </div>
      </header>

      <div className="domnai-admin-users-summary six-cards" aria-label="Resumo de usuários">
        <article><span>Total de usuários</span><strong>{formatNumber(summary.totalUsers)}</strong></article>
        <article><span>Novos esta semana</span><strong>{formatNumber(summary.newThisWeek)}</strong></article>
        <article><span>Novos este mês</span><strong>{formatNumber(summary.newThisMonth)}</strong></article>
        <article><span>Ativos em 7 dias</span><strong>{formatNumber(summary.activeLast7Days)}</strong></article>
        <article><span>Plano Free</span><strong>{formatNumber(summary.freeUsers)}</strong></article>
        <article><span>Plano Premium</span><strong>{formatNumber(summary.premiumUsers)}</strong></article>
      </div>

      {dataWarning ? (
        <div className="domnai-admin-users-data-warning" role="status">
          <strong>Atualização parcial</strong>
          <span>{dataWarning}</span>
        </div>
      ) : null}

      {status === 'loading' ? (
        <div className="domnai-admin-users-state">
          <span className="spinner" />
          Carregando usuários reais...
        </div>
      ) : null}

      {status === 'error' ? (
        <div className="domnai-admin-users-state error">
          <strong>Não foi possível carregar o módulo Usuários.</strong>
          <p>{error}</p>
          <button type="button" onClick={() => loadUsers()}>Tentar novamente</button>
        </div>
      ) : null}

      {status === 'ready' ? (
        <>
          <div className="domnai-admin-users-analytics">
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

          <section className="domnai-admin-users-brain" aria-label="Leitura IAttom Brain">
            <header>
              <div className="brain-mark">IB</div>
              <div>
                <span>IAttom Brain</span>
                <strong>Leitura automática da base de usuários</strong>
              </div>
            </header>
            <div className="brain-grid">
              {brainInsights.map((insight, index) => (
                <article className={insight.level || 'info'} key={`${insight.title}-${index}`}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div>
                    <strong>{insight.title}</strong>
                    <p>{insight.message}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <div className="domnai-admin-users-toolbar">
            <label className="search-field">
              <span>Buscar usuário</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Nome ou e-mail"
              />
            </label>

            <label>
              <span>Plano</span>
              <select value={planFilter} onChange={(event) => setPlanFilter(event.target.value)}>
                {PLAN_FILTERS.map((item) => (
                  <option value={item.value} key={item.value}>{item.label}</option>
                ))}
              </select>
            </label>

            <label>
              <span>Função</span>
              <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}>
                {ROLE_FILTERS.map((item) => (
                  <option value={item.value} key={item.value}>{item.label}</option>
                ))}
              </select>
            </label>

            <div className="result-count">
              <span>Exibindo</span>
              <strong>{formatNumber(visibleUsers.length)} de {formatNumber(items.length)}</strong>
            </div>
          </div>

          {visibleUsers.length === 0 ? (
            <div className="domnai-admin-users-state compact">
              <strong>Nenhum usuário encontrado</strong>
              <p>Ajuste a busca ou os filtros aplicados.</p>
            </div>
          ) : (
            <div className="domnai-admin-users-table-wrap">
              <table className="domnai-admin-users-table">
                <thead>
                  <tr>
                    <th>Usuário</th>
                    <th>Função</th>
                    <th>Plano</th>
                    <th>Créditos</th>
                    <th>Perfil</th>
                    <th>Cadastro</th>
                    <th>Última atividade</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleUsers.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="user-cell">
                          <span className="avatar">{initials(item.name)}</span>
                          <div>
                            <strong>{item.name}</strong>
                            <small>{item.email || 'E-mail não disponível'}</small>
                          </div>
                        </div>
                      </td>
                      <td><span className={`role-badge ${item.role}`}>{item.roleLabel}</span></td>
                      <td>
                        <div className="plan-cell">
                          <strong>{item.planLabel}</strong>
                          <small>{item.accountStatusLabel}</small>
                        </div>
                      </td>
                      <td><strong className="credits">{formatNumber(item.totalCredits)}</strong></td>
                      <td>
                        <span className={`profile-badge ${item.profileCompleted ? 'complete' : 'pending'}`}>
                          {item.profileCompleted ? 'Completo' : 'Pendente'}
                        </span>
                      </td>
                      <td>
                        <time dateTime={item.createdAt || undefined}>
                          {formatDate(item.createdAt)}
                        </time>
                      </td>
                      <td>
                        <time dateTime={item.lastActivityAt || undefined}>
                          {formatDate(item.lastActivityAt, true)}
                        </time>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </section>
  );
}
