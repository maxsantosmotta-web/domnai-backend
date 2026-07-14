import React, { useEffect, useState } from 'react';
import { useAuth, useClerk, useUser } from '@clerk/clerk-react';
import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';
import './admin-access-boundary.css';

const OWNER_EMAIL = 'maxsantosmotta@gmail.com';
const ACCESS_MODE_KEY = 'domnai:access-mode:v1';

const ADMIN_SECTIONS = [
  'Visão geral',
  'Saúde operacional',
  'Usuários',
  'Faturamento',
  'Erros e alertas',
  'Auditoria',
  'Feedbacks',
];

function currentHashPath() {
  return window.location.hash.replace(/^#/, '') || '/';
}

function navigateTo(path) {
  const nextHash = `#${path}`;
  if (window.location.hash !== nextHash) window.location.hash = path;
}

function AccessLoading() {
  return (
    <main className="domnai-admin-gate-page" aria-busy="true">
      <section className="domnai-admin-gate-card compact">
        <img src={DOMNAI_LOGO} alt="DomnAI" />
        <span className="domnai-admin-spinner" aria-hidden="true" />
        <p>Validando seu acesso administrativo...</p>
      </section>
    </main>
  );
}

function AccessValidationError({ diagnostic, onRetry, onUser, onSignOut }) {
  return (
    <main className="domnai-admin-gate-page">
      <section className="domnai-admin-gate-card compact">
        <img src={DOMNAI_LOGO} alt="DomnAI" />
        <h1>Não foi possível validar o acesso administrativo.</h1>
        <p>O Painel ADM permaneceu bloqueado. Você pode tentar novamente ou retornar ao Painel Usuário.</p>
        {diagnostic ? <p><strong>Diagnóstico:</strong> {diagnostic}</p> : null}
        <div className="domnai-admin-error-actions">
          <button type="button" className="primary" onClick={onRetry}>Tentar novamente</button>
          <button type="button" onClick={onUser}>Painel Usuário</button>
        </div>
        <button type="button" className="domnai-admin-signout-link" onClick={onSignOut}>Sair da conta</button>
      </section>
    </main>
  );
}

function AdminPortalShell({ onUser, onSignOut }) {
  return (
    <main className="domnai-admin-shell">
      <aside className="domnai-admin-sidebar">
        <div className="domnai-admin-brand">
          <img src={DOMNAI_LOGO} alt="DomnAI" />
          <span>Painel Administrativo</span>
        </div>

        <nav aria-label="Monitoramento administrativo">
          {ADMIN_SECTIONS.map((section, index) => (
            <button type="button" className={index === 0 ? 'active' : ''} key={section} disabled={index !== 0}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              {section}
            </button>
          ))}
        </nav>

        <div className="domnai-admin-sidebar-actions">
          <button type="button" onClick={onUser}>Painel Usuário</button>
          <button type="button" onClick={onSignOut}>Sair da conta</button>
        </div>
      </aside>

      <section className="domnai-admin-workspace">
        <header className="domnai-admin-topbar">
          <div>
            <span>DomnAI · Administração</span>
            <h1>Visão geral</h1>
          </div>
          <span className="domnai-admin-protected-badge">Acesso protegido</span>
        </header>

        <section className="domnai-admin-foundation-card">
          <span className="domnai-admin-foundation-kicker">Fase 1</span>
          <h2>Ambiente administrativo isolado</h2>
          <p>
            A estrutura de acesso foi separada do ambiente dos usuários. Os dados, gráficos e recursos de monitoramento serão conectados nas próximas etapas sem alterar o Dashboard do cliente.
          </p>
          <div className="domnai-admin-foundation-status">
            <span><strong>Proteção</strong> validação administrativa no backend</span>
            <span><strong>Usuário</strong> experiência atual preservada</span>
            <span><strong>ADM</strong> arquivos e estilos exclusivos</span>
          </div>
        </section>
      </section>
    </main>
  );
}

export default function AdminAccessBoundary({ children }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { isLoaded: userLoaded, user } = useUser();
  const { signOut } = useClerk();
  const [route, setRoute] = useState(currentHashPath);
  const [verification, setVerification] = useState({ status: 'idle', isAdmin: false, message: '' });
  const [retryKey, setRetryKey] = useState(0);

  const primaryEmail = String(user?.primaryEmailAddress?.emailAddress || '').trim().toLowerCase();
  const isOwnerCandidate = primaryEmail === OWNER_EMAIL;
  const adminRoute = route === '/admin' || route.startsWith('/admin/');

  useEffect(() => {
    const handleHashChange = () => setRoute(currentHashPath());
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    if (!isOwnerCandidate) {
      delete window.openDomnAIAdmin;
      return undefined;
    }

    const openAdmin = () => {
      sessionStorage.setItem(ACCESS_MODE_KEY, 'admin');
      navigateTo('/admin');
    };

    window.openDomnAIAdmin = openAdmin;
    return () => {
      if (window.openDomnAIAdmin === openAdmin) delete window.openDomnAIAdmin;
    };
  }, [isOwnerCandidate]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !userLoaded || !isOwnerCandidate || !adminRoute) {
      setVerification({ status: 'idle', isAdmin: false, message: '' });
      return undefined;
    }

    let cancelled = false;
    setVerification({ status: 'checking', isAdmin: false, message: '' });

    (async () => {
      try {
        const token = await getToken();
        const response = await fetch('/api/auth/access-mode', {
          headers: { Authorization: `Bearer ${token}` },
          cache: 'no-store',
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || 'Não foi possível validar o acesso administrativo.');
        if (!cancelled) {
          setVerification({ status: 'verified', isAdmin: payload.isAdmin === true, message: '' });
        }
      } catch (error) {
        if (!cancelled) {
          setVerification({
            status: 'error',
            isAdmin: false,
            message: error?.message || 'Não foi possível validar o acesso administrativo.',
          });
        }
      }
    })();

    return () => { cancelled = true; };
  }, [adminRoute, getToken, isLoaded, isOwnerCandidate, isSignedIn, retryKey, userLoaded]);

  useEffect(() => {
    if (!isSignedIn) sessionStorage.removeItem(ACCESS_MODE_KEY);
  }, [isSignedIn]);

  function selectUserAccess() {
    sessionStorage.setItem(ACCESS_MODE_KEY, 'user');
    navigateTo('/');
  }

  async function leaveAccount() {
    sessionStorage.removeItem(ACCESS_MODE_KEY);
    await signOut({ redirectUrl: '/#/' });
  }

  if (!adminRoute) return children;
  if (!isLoaded || !isSignedIn || !userLoaded) return <AccessLoading />;
  if (!isOwnerCandidate) return children;
  if (verification.status === 'idle' || verification.status === 'checking') return <AccessLoading />;

  if (verification.status === 'error') {
    return (
      <AccessValidationError
        diagnostic={verification.message}
        onRetry={() => setRetryKey((current) => current + 1)}
        onUser={selectUserAccess}
        onSignOut={leaveAccount}
      />
    );
  }

  if (!verification.isAdmin) {
    return (
      <AccessValidationError
        diagnostic="A conta autenticada não possui autorização administrativa."
        onRetry={() => setRetryKey((current) => current + 1)}
        onUser={selectUserAccess}
        onSignOut={leaveAccount}
      />
    );
  }

  return <AdminPortalShell onUser={selectUserAccess} onSignOut={leaveAccount} />;
}
