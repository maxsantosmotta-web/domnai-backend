import React, { useEffect } from 'react';
import {
  SignInButton,
  SignUpButton,
  UserButton,
  useAuth,
} from '@clerk/clerk-react';
import { DOMNAI_LOGO } from './logoData';

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

function Landing() {
  return (
    <main className="landing-page">
      <section className="landing-card" aria-label="Acesso ao DomnAI">
        <img
          className="official-logo"
          src={DOMNAI_LOGO}
          alt="DomnAI — Transforme escolhas em resultados com inteligência."
        />

        <div className="access-actions">
          <SignUpButton mode="modal" forceRedirectUrl="/">
            <button className="primary-button" type="button">Criar conta</button>
          </SignUpButton>

          <SignInButton mode="modal" forceRedirectUrl="/">
            <button className="secondary-button" type="button">Fazer login</button>
          </SignInButton>
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
        <img
          className="dashboard-logo"
          src={DOMNAI_LOGO}
          alt="DomnAI"
        />
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

  if (!isLoaded) {
    return <Splash />;
  }

  if (!isSignedIn) {
    return <Landing />;
  }

  return <Dashboard />;
}
