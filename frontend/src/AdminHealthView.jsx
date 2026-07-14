import React, { useCallback, useEffect, useMemo, useState } from 'react';
import './admin-health-view.css';

const EMPTY_HEALTH = {
  status: 'loading',
  statusLabel: 'Verificando...',
  app: 'DomnAI',
  version: '',
  environment: '',
  checkedAt: '',
  serverCheckMs: null,
  dependencies: {
    database: { configured: false, reachable: false, latencyMs: null },
    openaiConfigured: false,
    clerkConfigured: false,
    stripeConfigured: false,
    pdfGeneratorAvailable: false,
  },
};

function formatDate(value) {
  if (!value) return 'Sem verificação';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Sem verificação';
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function latencyLabel(value) {
  if (value === null || value === undefined) return 'Sem medição';
  return `${Number(value).toLocaleString('pt-BR')} ms`;
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

function serviceStatus(ready, readyLabel = 'Configurado') {
  return ready
    ? { state: 'ready', label: readyLabel }
    : { state: 'attention', label: 'Ausente' };
}

export default function AdminHealthView() {
  const [health, setHealth] = useState(EMPTY_HEALTH);
  const [apiLatency, setApiLatency] = useState(null);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  const loadHealth = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setStatus('loading');
    setError('');
    const startedAt = performance.now();

    try {
      const response = await fetch('/health', { cache: 'no-store' });
      const payload = await readResponse(response);
      const measuredLatency = Math.round(performance.now() - startedAt);
      if (!response.ok) {
        throw new Error(payload.detail || `Falha ao verificar a saúde operacional (${response.status}).`);
      }
      setHealth({ ...EMPTY_HEALTH, ...payload, dependencies: { ...EMPTY_HEALTH.dependencies, ...(payload.dependencies || {}) } });
      setApiLatency(measuredLatency);
      setStatus('ready');
    } catch (loadError) {
      setApiLatency(Math.round(performance.now() - startedAt));
      if (!silent) {
        setError(loadError?.message || 'Não foi possível verificar a saúde operacional.');
        setStatus('error');
      }
    }
  }, []);

  useEffect(() => {
    loadHealth();
    const interval = window.setInterval(() => loadHealth({ silent: true }), 15000);
    return () => window.clearInterval(interval);
  }, [loadHealth]);

  const services = useMemo(() => {
    const dependencies = health.dependencies || EMPTY_HEALTH.dependencies;
    const database = dependencies.database || EMPTY_HEALTH.dependencies.database;
    const databaseStatus = database.reachable
      ? { state: 'ready', label: 'Online' }
      : database.configured
        ? { state: 'offline', label: 'Indisponível' }
        : { state: 'attention', label: 'Ausente' };

    return [
      {
        name: 'API DomnAI',
        status: { state: status === 'ready' ? 'ready' : 'offline', label: status === 'ready' ? 'Online' : 'Indisponível' },
        detail: `Resposta total: ${latencyLabel(apiLatency)}`,
      },
      {
        name: 'Banco de dados',
        status: databaseStatus,
        detail: database.reachable ? `Latência: ${latencyLabel(database.latencyMs)}` : 'Conexão não confirmada',
      },
      {
        name: 'OpenAI',
        status: serviceStatus(Boolean(dependencies.openaiConfigured)),
        detail: dependencies.openaiConfigured ? 'Chave disponível no servidor' : 'Chave não configurada',
      },
      {
        name: 'Clerk',
        status: serviceStatus(Boolean(dependencies.clerkConfigured)),
        detail: dependencies.clerkConfigured ? 'Autenticação configurada' : 'Autenticação não configurada',
      },
      {
        name: 'Stripe',
        status: serviceStatus(Boolean(dependencies.stripeConfigured)),
        detail: dependencies.stripeConfigured ? 'Pagamentos configurados' : 'Pagamentos não configurados',
      },
      {
        name: 'Gerador de PDF',
        status: serviceStatus(Boolean(dependencies.pdfGeneratorAvailable), 'Disponível'),
        detail: dependencies.pdfGeneratorAvailable ? 'Serviço carregado no backend' : 'Serviço indisponível',
      },
    ];
  }, [apiLatency, health.dependencies, status]);

  const readyCount = services.filter((service) => service.status.state === 'ready').length;
  const attentionCount = services.length - readyCount;

  function handleRefresh(event) {
    event.currentTarget.blur();
    loadHealth();
  }

  return (
    <section className="domnai-admin-health-view" aria-label="Saúde operacional">
      <header className="domnai-admin-health-heading">
        <div>
          <span className="health-live-indicator"><i />Monitoramento real · atualização automática</span>
          <small>{health.checkedAt ? `Última verificação: ${formatDate(health.checkedAt)}` : 'Verificando serviços...'}</small>
        </div>
        <button type="button" onClick={handleRefresh} disabled={status === 'loading'}>
          {status === 'loading' ? 'Atualizando...' : 'Atualizar'}
        </button>
      </header>

      <section className={`domnai-admin-health-overall ${health.status === 'ok' && status === 'ready' ? 'ready' : 'attention'}`}>
        <div>
          <span>Estado geral</span>
          <strong>{status === 'ready' ? health.statusLabel : status === 'error' ? 'Indisponível' : 'Verificando...'}</strong>
          <p>{status === 'ready' ? `${health.app} · ${health.environment || 'ambiente atual'}${health.version ? ` · versão ${health.version}` : ''}` : 'Aguardando resposta da plataforma.'}</p>
        </div>
        <div className="health-overall-numbers">
          <span><strong>{readyCount}</strong> prontos</span>
          <span><strong>{attentionCount}</strong> atenções</span>
          <span><strong>{latencyLabel(health.serverCheckMs)}</strong> verificação interna</span>
        </div>
      </section>

      {status === 'error' ? (
        <div className="domnai-admin-health-state error">
          <strong>Não foi possível verificar a Saúde operacional.</strong>
          <p>{error}</p>
          <button type="button" onClick={() => loadHealth()}>Tentar novamente</button>
        </div>
      ) : null}

      <div className="domnai-admin-health-services" aria-label="Serviços monitorados">
        {services.map((service) => (
          <article className={service.status.state} key={service.name}>
            <div className="health-service-title">
              <i />
              <span>{service.name}</span>
            </div>
            <strong>{service.status.label}</strong>
            <small>{service.detail}</small>
          </article>
        ))}
      </div>

      <p className="domnai-admin-health-note">
        API e banco são testados em cada atualização. OpenAI, Clerk e Stripe indicam se a configuração necessária está presente no servidor.
      </p>
    </section>
  );
}
