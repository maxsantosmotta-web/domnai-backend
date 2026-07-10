import React, { useEffect, useState } from 'react';
import {
  SignInButton,
  SignUpButton,
  UserButton,
  useAuth,
  useClerk,
  useSession,
  useUser,
} from '@clerk/clerk-react';
import { DOMNAI_LOGO } from './logoData';

const SPLASH_LIMIT_MS = 1200;

function Splash() {
  return (
    <main className="startup-page" aria-live="polite" aria-busy="true">
      <div>
        <h1>DomnAI</h1>
        <p>Verificando acesso...</p>
      </div>
    </main>
  );
}

function AuthDiagnostics() {
  const auth = useAuth();
  const { user, isLoaded: isUserLoaded } = useUser();
  const { session, isLoaded: isSessionLoaded } = useSession();
  const clerk = useClerk();

  useEffect(() => {
    console.info('[DomnAI][Clerk]', {
      isLoaded: auth.isLoaded,
      isSignedIn: auth.isSignedIn,
      userLoaded: isUserLoaded,
      user: user?.id ?? null,
      sessionLoaded: isSessionLoaded,
      session: session?.id ?? null,
      clerkLoaded: Boolean(clerk?.loaded),
      origin: window.location.origin,
    });
  }, [auth.isLoaded, auth.isSignedIn, clerk, isSessionLoaded, isUserLoaded, session?.id, user?.id]);

  return null;
}

function AuthBridge() {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    if (!isSignedIn) return;

    const validateSession = async () => {
      const token = await getToken();
      const response = await fetch('/api/auth/status', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        console.error('[DomnAI] Falha ao validar a sessão no backend.');
      }
    };

    validateSession().catch((error) => {
      console.error('[DomnAI] Erro ao validar a sessão:', error);
    });
  }, [getToken, isSignedIn]);

  return null;
}

function Landing({ authReady }) {
  return (
    <main className="landing-page">
      <section className="landing-card" aria-label="Acesso ao DomnAI">
        <img
          className="official-logo"
          src={DOMNAI_LOGO}
          alt="DomnAI — Transforme escolhas em resultados com inteligência."
        />

        <div className="access-actions">
          {authReady ? (
            <>
              <SignUpButton mode="modal" forceRedirectUrl="/">
                <button className="primary-button" type="button">Criar conta</button>
              </SignUpButton>

              <SignInButton mode="modal" forceRedirectUrl="/">
                <button className="secondary-button" type="button">Fazer login</button>
              </SignInButton>
            </>
          ) : (
            <>
              <button className="primary-button" type="button" disabled>Carregando acesso</button>
              <button className="secondary-button" type="button" disabled>Fazer login</button>
            </>
          )}
        </div>
      </section>

      <footer className="landing-footer">
        <a href="/sobre">Sobre</a>
        <a href="/privacidade">Privacidade</a>
        <a href="/termos">Termos</a>
        <a href="/contato">Contato</a>
      </footer>
    </main>
  );
}

function Dashboard() {
  return (
    <main className="dashboard-page">
      <AuthBridge />
      <header className="dashboard-header">
        <img className="dashboard-logo" src={DOMNAI_LOGO} alt="DomnAI" />
        <UserButton afterSignOutUrl="/" />
      </header>

      <section className="dashboard-content">
        <p className="dashboard-eyebrow">Acesso confirmado</p>
        <h1>Bem-vindo ao DomnAI</h1>
        <p>Transforme escolhas em resultados com inteligência.</p>
      </section>
    </main>
  );
}

export default function App() {
  const { isLoaded, isSignedIn } = useAuth();
  const [splashExpired, setSplashExpired] = useState(false);

  useEffect(() => {
    if (isLoaded) {
      setSplashExpired(true);
      return undefined;
    }

    const timer = window.setTimeout(() => {
      console.error('[DomnAI][Clerk] Inicialização excedeu 1200 ms. Exibindo a Landing sem bloquear a interface.');
      setSplashExpired(true);
    }, SPLASH_LIMIT_MS);

    return () => window.clearTimeout(timer);
  }, [isLoaded]);

  return (
    <>
      <AuthDiagnostics />
      {!isLoaded && !splashExpired ? <Splash /> : null}
      {!isLoaded && splashExpired ? <Landing authReady={false} /> : null}
      {isLoaded && !isSignedIn ? <Landing authReady /> : null}
      {isLoaded && isSignedIn ? <Dashboard /> : null}
    </>
  );
}
