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
        <p>Validando seu tipo de acesso...</p>
      </section>
    </main>
  );
}

function AccessChoice({ onAdmin, onUser, onSignOut }) {
  return (
    <main className="domnai-admin-gate-page">
      <section className="domnai-admin-gate-card">
        <img src={DOMNAI_LOGO} alt="DomnAI" />
        <div className="domnai-admin-gate-heading">
          <span>Conta administrativa reconhecida</span>
          <h1>Como deseja acessar o DomnAI?</h1>
          <p>Escolha o ambiente que deseja utilizar nesta sessão.</p>
        </div>

        <div className="domnai-admin-access-options">
          <button type="button" className="domnai-admin-access-option primary" onClick={onAdmin}>
            <span className="domnai-admin-access-icon">ADM</span>
            <strong>Acesso Administrativo</strong>
            <small>Monitoramento, usuários, faturamento, alertas e feedbacks.</small>
          </button>

          <button type="button" className="domnai-admin-access-option" onClick={onUser}>
            <span className="domnai-admin-access-icon">USER</span>
            <strong>Acesso Usuário</strong>
            <small>Abra o DomnAI exatamente como a plataforma é exibida ao cliente.</small>
          </button>
        </div>

        <button type="button" className="domnai-admin-signout-link" onClick={onSignOut}>
          Sair da conta
        </button>
      </section>
    </main>
  );
}

function AccessValidationError({ onRetry, onUser, onSignOut }) {
  return (
    <main className="domnai-admin-gate-page">
      <section className="domnai-admin-gate-card compact">
        <img src={DOMNAI_LOGO} alt="DomnAI" />
        <h1>Não foi possível validar o acesso administrativo.</h1>
        <p>O ambiente administrativo permaneceu bloqueado. Você pode tentar novamente ou continuar no acesso de usuário.</p>
        <div className="domnai-admin-error-actions">
          <button type="button" className="primary" onClick={onRetry}>Tentar novamente</button>
          <button type="button" onClick={onUser}>Acessar como usuário</button>
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
          <button type="button" onClick={onUser}>Acesso Usuário</button>
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

function AdminReturnButton({ onAdmin }) {
  return (
    <button type="button" className="domnai-admin-return-button" onClick={onAdmin}>
      Acesso Administrativo
    </button>
  );
}

export default function AdminAccessBoundary({ children }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { isLoaded: userLoaded, user } = useUser();
  const { signOut } = useClerk();
  const [route, setRoute] = useState(currentHashPath);
  const [accessMode, setAccessMode] = useState(() => sessionStorage.getItem(ACCESS_MODE_KEY) || '');
  const [verification, setVerification] = useState({ status: 'idle', isAdmin: false });
  const [retryKey, setRetryKey] = useState(0);

  const primaryEmail = String(user?.primaryEmailAddress?.emailAddress || '').trim().toLowerCase();
  const isOwnerCandidate = primaryEmail === OWNER_EMAIL;

  useEffect(() => {
    const handleHashChange = () => setRoute(currentHashPath());
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !userLoaded || !isOwnerCandidate) {
      setVerification({ status: 'idle', isAdmin: false });
      return undefined;
    }

    let cancelled = false;
    setVerification({ status: 'checking', isAdmin: false });

    (async () => {
      try {
        const token = await getToken();
        const response = await fetch('/api/auth/access-mode', {
          headers: { Authorization: `Bearer ${token}` },
          cache: 'no-store',
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || 'Não foi possível validar o acesso administrativo.');
        if (!cancelled) setVerification({ status: 'verified', isAdmin: payload.isAdmin === true });
      } catch {
        if (!cancelled) setVerification({ status: 'error', isAdmin: false });
      }
    })();

    return () => { cancelled = true; };
  }, [getToken, isLoaded, isOwnerCandidate, isSignedIn, retryKey, userLoaded]);

  useEffect(() => {
    if (!isSignedIn) {
      sessionStorage.removeItem(ACCESS_MODE_KEY);
      setAccessMode('');
    }
  }, [isSignedIn]);

  function selectAdminAccess() {
    sessionStorage.setItem(ACCESS_MODE_KEY, 'admin');
    setAccessMode('admin');
    navigateTo('/admin');
  }

  function selectUserAccess() {
    sessionStorage.setItem(ACCESS_MODE_KEY, 'user');
    setAccessMode('user');
    navigateTo('/');
  }

  async function leaveAccount() {
    sessionStorage.removeItem(ACCESS_MODE_KEY);
    setAccessMode('');
    await signOut({ redirectUrl: '/#/' });
  }

  if (!isLoaded || !isSignedIn) return children;
  if (!userLoaded) return <AccessLoading />;
  if (!isOwnerCandidate) return children;

  const adminRoute = route === '/admin' || route.startsWith('/admin/');

  if (accessMode === 'user') {
    return (
      <>
        {children}
        {verification.status === 'verified' && verification.isAdmin ? (
          <AdminReturnButton onAdmin={selectAdminAccess} />
        ) : null}
      </>
    );
  }

  if (verification.status === 'idle' || verification.status === 'checking') return <AccessLoading />;

  if (verification.status === 'error') {
    if (accessMode === 'admin' || adminRoute) {
      return (
        <AccessValidationError
          onRetry={() => setRetryKey((current) => current + 1)}
          onUser={selectUserAccess}
          onSignOut={leaveAccount}
        />
      );
    }
    return children;
  }

  if (!verification.isAdmin) return children;

  if (adminRoute || accessMode === 'admin') {
    return <AdminPortalShell onUser={selectUserAccess} onSignOut={leaveAccount} />;
  }

  return <AccessChoice onAdmin={selectAdminAccess} onUser={selectUserAccess} onSignOut={leaveAccount} />;
}
