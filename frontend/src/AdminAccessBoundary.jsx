import React, { useEffect, useState } from 'react';
import { useAuth, useClerk, useUser } from '@clerk/clerk-react';
import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';
import './admin-access-boundary.css';
import './admin-user-sidebar-entry.css';

const OWNER_EMAIL = 'maxsantosmotta@gmail.com';
const ADMIN_ENTRY_KEY = 'domnai:admin-requested:v1';

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
        <p>O Painel Adm permaneceu bloqueado. Você pode tentar novamente ou retornar ao Painel Usuário.</p>
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
          <span>Painel Adm</span>
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
            <span><strong>Adm</strong> arquivos e estilos exclusivos</span>
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
  const adminRequested = sessionStorage.getItem(ADMIN_ENTRY_KEY) === 'true';

  useEffect(() => {
    const handleHashChange = () => setRoute(currentHashPath());
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !userLoaded || !isOwnerCandidate || adminRoute) {
      document.querySelector('[data-domnai-admin-menu]')?.remove();
      return undefined;
    }

    let cancelled = false;
    let animationFrame = 0;
    let entry = null;
    let button = null;

    const openAdmin = () => {
      sessionStorage.setItem(ADMIN_ENTRY_KEY, 'true');
      navigateTo('/admin');
    };

    const installEntry = (attempt = 0) => {
      if (cancelled) return;
      const navigation = document.querySelector('.sidebar-navigation');
      if (!navigation) {
        if (attempt < 20) animationFrame = window.requestAnimationFrame(() => installEntry(attempt + 1));
        return;
      }

      entry = navigation.querySelector('[data-domnai-admin-menu]');
      if (!entry) {
        entry = document.createElement('div');
        entry.className = 'sidebar-group domnai-user-admin-group';
        entry.dataset.domnaiAdminMenu = 'true';
        entry.innerHTML = '<p>Admin</p><button type="button" class="domnai-user-admin-button"><span>◇</span> Painel Adm <small>ADM</small></button>';
        navigation.appendChild(entry);
      }

      button = entry.querySelector('.domnai-user-admin-button');
      button?.addEventListener('click', openAdmin);
    };

    installEntry();

    return () => {
      cancelled = true;
      if (animationFrame) window.cancelAnimationFrame(animationFrame);
      button?.removeEventListener('click', openAdmin);
      entry?.remove();
    };
  }, [adminRoute, isLoaded, isOwnerCandidate, isSignedIn, userLoaded]);

  useEffect(() => {
    if (!isSignedIn) sessionStorage.removeItem(ADMIN_ENTRY_KEY);
  }, [isSignedIn]);

  useEffect(() => {
    if (!adminRoute) return;
    if (!adminRequested || (userLoaded && !isOwnerCandidate)) {
      sessionStorage.removeItem(ADMIN_ENTRY_KEY);
      navigateTo('/');
    }
  }, [adminRequested, adminRoute, isOwnerCandidate, userLoaded]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !userLoaded || !isOwnerCandidate || !adminRoute || !adminRequested) {
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
  }, [adminRequested, adminRoute, getToken, isLoaded, isOwnerCandidate, isSignedIn, retryKey, userLoaded]);

  function selectUserAccess() {
    sessionStorage.removeItem(ADMIN_ENTRY_KEY);
    navigateTo('/');
  }

  async function leaveAccount() {
    sessionStorage.removeItem(ADMIN_ENTRY_KEY);
    await signOut({ redirectUrl: '/#/' });
  }

  if (!adminRoute || !adminRequested) return children;
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
