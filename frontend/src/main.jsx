import React from 'react';
import ReactDOM from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './styles.css';

async function startApplication() {
  const response = await fetch('/api/config/public');

  if (!response.ok) {
    throw new Error('Não foi possível carregar a configuração do DomnAI.');
  }

  const { clerkPublishableKey } = await response.json();

  if (!clerkPublishableKey) {
    throw new Error('Chave pública do Clerk não configurada.');
  }

  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <ClerkProvider publishableKey={clerkPublishableKey} afterSignOutUrl="/">
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ClerkProvider>
    </React.StrictMode>,
  );
}

startApplication().catch((error) => {
  console.error(error);
  document.getElementById('root').innerHTML = `
    <main style="min-height:100vh;display:grid;place-items:center;background:#050505;color:#fff;font-family:system-ui;padding:24px;text-align:center">
      <div>
        <h1 style="margin:0 0 12px">DomnAI</h1>
        <p style="margin:0;color:#b8b8b8">Não foi possível iniciar a aplicação.</p>
      </div>
    </main>
  `;
});
