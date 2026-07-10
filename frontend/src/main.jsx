import React from 'react';
import ReactDOM from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './styles.css';

const rootElement = document.getElementById('root');

rootElement.innerHTML = `
  <main style="min-height:100vh;display:grid;place-items:center;background:#050505;color:#fff;font-family:system-ui;padding:24px;text-align:center">
    <div>
      <h1 style="margin:0 0 12px;font-size:2rem">DomnAI</h1>
      <p style="margin:0;color:#b8b8b8">Carregando acesso seguro...</p>
    </div>
  </main>
`;

async function startApplication() {
  const response = await fetch('/api/config/public', { cache: 'no-store' });

  if (!response.ok) {
    throw new Error('Não foi possível carregar a configuração do DomnAI.');
  }

  const { clerkPublishableKey } = await response.json();

  if (!clerkPublishableKey) {
    throw new Error('Chave pública do Clerk não configurada.');
  }

  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <ClerkProvider
        publishableKey={clerkPublishableKey}
        isSatellite
        domain={window.location.hostname}
        signInUrl="/"
        signUpUrl="/"
        signInFallbackRedirectUrl="/"
        signUpFallbackRedirectUrl="/"
        afterSignOutUrl="/"
      >
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ClerkProvider>
    </React.StrictMode>,
  );
}

startApplication().catch((error) => {
  console.error(error);
  rootElement.innerHTML = `
    <main style="min-height:100vh;display:grid;place-items:center;background:#050505;color:#fff;font-family:system-ui;padding:24px;text-align:center">
      <div>
        <h1 style="margin:0 0 12px">DomnAI</h1>
        <p style="margin:0;color:#b8b8b8">Não foi possível iniciar a autenticação.</p>
        <button onclick="window.location.reload()" style="margin-top:18px;padding:12px 18px;border:1px solid #d5aa35;border-radius:10px;background:#d5aa35;color:#050505;font-weight:700">Tentar novamente</button>
      </div>
    </main>
  `;
});
