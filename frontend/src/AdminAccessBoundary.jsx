import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useAuth, useClerk, useUser } from '@clerk/clerk-react';
import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';
import './admin-access-boundary.css';
import './admin-user-sidebar-entry.css';
import './admin-profile-shell.css';

const OWNER_EMAIL = 'maxsantosmotta@gmail.com';
const ADMIN_ENTRY_KEY = 'domnai:admin-requested:v1';
const PROFILE_CACHE_KEY = 'domnai:profile:v1';

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

function readCachedProfile() {
  try {
    return JSON.parse(sessionStorage.getItem(PROFILE_CACHE_KEY) || 'null')?.profile || {};
  } catch {
    return {};
  }
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

function AdminProfileCard({ profile, user, avatarUrl }) {
  const email = String(user?.primaryEmailAddress?.emailAddress || '');
  const name = String(profile?.fullName || user?.fullName || user?.firstName || 'Minha conta');
  const image = avatarUrl || user?.imageUrl || '';
  const initial = (name || email || 'A').trim().charAt(0).toUpperCase();

  return (
    <div className="domnai-admin-profile-card">
      <div className="domnai-admin-profile-avatar">
        {image ? <img src={image} alt="Foto do perfil" /> : <span>{initial}</span>}
      </div>
      <div className="domnai-admin-profile-copy">
        <strong>{name}</strong>
        <small>{email || 'Conta DomnAI'}</small>
      </div>
      <span className="domnai-admin-profile-role">Adm</span>
    </div>
  );
}

function AdminPortalShell({ onUser, onSignOut, profile, user, avatarUrl }) {
  return (
    <main className="domnai-admin-shell">
      <aside className="domnai-admin-sidebar">
        <div className="domnai-admin-brand">
          <img src={DOMNAI_LOGO} alt="DomnAI" />
          <span>Painel Adm</span>
        </div>

        <button type="button" className="domnai-admin-user-switch" onClick={onUser}>
          <span className="domnai-admin-user-switch-icon">↩</span>
          <span>
            <strong>Painel Usuário</strong>
            <small>Voltar ao ambiente de uso</small>
          </span>
        </button>

        <nav aria-label="Monitoramento administrativo">
          {ADMIN_SECTIONS.map((section, index) => (
            <button type="button" className={index === 0 ? 'active' : ''} key={section} disabled={index !== 0}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              {section}
            </button>
          ))}
        </nav>

        <div className="domnai-admin-sidebar-footer">
          <button type="button" className="domnai-admin-signout-button" onClick={onSignOut}>
            <span>↪</span>
            Sair da conta
          </button>
          <AdminProfileCard profile={profile} user={user} avatarUrl={avatarUrl} />
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

function UserAdminEntry({ onOpen }) {
  return (
    <div className="sidebar-group domnai-user-admin-group" data-domnai-admin-menu="true">
      <p>Admin</p>
      <button type="button" className="domnai-user-admin-button" onClick={onOpen}>
        <span>◇</span>
        Painel Adm
        <small>Adm</small>
      </button>
    </div>
  );
}

export default function AdminAccessBoundary({ children }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { isLoaded: userLoaded, user } = useUser();
  const { signOut } = useClerk();
  const [route, setRoute] = useState(currentHashPath);
  const [sidebarTarget, setSidebarTarget] = useState(null);
  const [verification, setVerification] = useState({ status: 'idle', isAdmin: false, message: '' });
  const [adminProfile, setAdminProfile] = useState(() => ({ profile: readCachedProfile(), avatarUrl: '' }));
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
      setSidebarTarget(null);
      return undefined;
    }

    const syncSidebarTarget = () => {
      const navigation = document.querySelector('.sidebar-navigation');
      setSidebarTarget((current) => {
        if (navigation?.isConnected) return current === navigation ? current : navigation;
        return current?.isConnected ? current : null;
      });
    };

    syncSidebarTarget();
    const interval = window.setInterval(syncSidebarTarget, 300);
    return () => window.clearInterval(interval);
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
        if (!cancelled) setVerification({ status: 'verified', isAdmin: payload.isAdmin === true, message: '' });
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

  useEffect(() => {
    if (verification.status !== 'verified' || !verification.isAdmin || !adminRoute) return undefined;

    let cancelled = false;
    let avatarObjectUrl = '';

    (async () => {
      try {
        const token = await getToken();
        const headers = { Authorization: `Bearer ${token}` };
        const [profileResponse, avatarResponse] = await Promise.all([
          fetch('/api/profile', { headers, cache: 'no-store' }),
          fetch('/api/profile/avatar', { headers, cache: 'no-store' }),
        ]);

        const profilePayload = profileResponse.ok ? await profileResponse.json() : null;
        if (avatarResponse.ok) avatarObjectUrl = URL.createObjectURL(await avatarResponse.blob());

        if (!cancelled) {
          setAdminProfile({
            profile: profilePayload?.profile || readCachedProfile(),
            avatarUrl: avatarObjectUrl,
          });
        }
      } catch {
        if (!cancelled) setAdminProfile((current) => ({ ...current, profile: current.profile || readCachedProfile() }));
      }
    })();

    return () => {
      cancelled = true;
      if (avatarObjectUrl) URL.revokeObjectURL(avatarObjectUrl);
    };
  }, [adminRoute, getToken, verification.isAdmin, verification.status]);

  function openAdminAccess() {
    sessionStorage.setItem(ADMIN_ENTRY_KEY, 'true');
    navigateTo('/admin');
  }

  function selectUserAccess() {
    sessionStorage.removeItem(ADMIN_ENTRY_KEY);
    navigateTo('/');
  }

  async function leaveAccount() {
    sessionStorage.removeItem(ADMIN_ENTRY_KEY);
    await signOut({ redirectUrl: '/#/' });
  }

  if (!adminRoute || !adminRequested) {
    return (
      <>
        {children}
        {isOwnerCandidate && sidebarTarget
          ? createPortal(<UserAdminEntry onOpen={openAdminAccess} />, sidebarTarget)
          : null}
      </>
    );
  }

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

  return (
    <AdminPortalShell
      onUser={selectUserAccess}
      onSignOut={leaveAccount}
      profile={adminProfile.profile}
      user={user}
      avatarUrl={adminProfile.avatarUrl}
    />
  );
}
