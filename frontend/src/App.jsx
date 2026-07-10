import { useEffect } from 'react';
import {
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
  useAuth,
} from '@clerk/clerk-react';

const API_URL = import.meta.env.VITE_API_URL || 'https://domnai.iattomassist.com.br';

function AuthBridge() {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    if (!isSignedIn) return;

    const validateSession = async () => {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/auth/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        console.error('Falha ao validar a sessão do DomnAI.');
      }
    };

    validateSession().catch(console.error);
  }, [getToken, isSignedIn]);

  return null;
}

export default function App() {
  return (
    <main className="landing-page">
      <AuthBridge />

      <section className="landing-card" aria-label="Acesso ao DomnAI">
        <img
          className="official-logo"
          src="/domnai-logo.png"
          alt="DomnAI — Transforme escolhas em resultados com inteligência."
        />

        <SignedOut>
          <div className="access-actions">
            <SignUpButton mode="modal" forceRedirectUrl="/">
              <button className="primary-button" type="button">Criar conta</button>
            </SignUpButton>

            <SignInButton mode="modal" forceRedirectUrl="/">
              <button className="secondary-button" type="button">Fazer login</button>
            </SignInButton>
          </div>
        </SignedOut>

        <SignedIn>
          <div className="signed-area">
            <span>Acesso confirmado</span>
            <UserButton />
          </div>
        </SignedIn>
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
