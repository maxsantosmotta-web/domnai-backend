import React from 'react';
import ReactDOM from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';
import { HashRouter } from 'react-router-dom';
import App from './App';
import ErrorBoundary from './ErrorBoundary';
import './styles.css';

const rootElement = document.getElementById('root');

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function renderStartupError(error) {
  const message = escapeHtml(error?.message || error || 'Erro desconhecido.');

  console.error('[DomnAI] Falha na inicialização:', error);
  rootElement.innerHTML = `
    <main class="runtime-error-page" role="alert">
      <section class="runtime-error-card">
        <h1>DomnAI</h1>
        <h2>Não foi possível concluir a abertura.</h2>
        <p>${message}</p>
        <button type="button" onclick="window.location.reload()">Tentar novamente</button>
      </section>
    </main>
  `;
}

window.onerror = (message, source, lineno, colno, error) => {
  console.error('[DomnAI] Erro global:', { message, source, lineno, colno, error });
};

window.onunhandledrejection = (event) => {
  console.error('[DomnAI] Promise rejeitada sem tratamento:', event.reason);
};

async function startApplication() {
  const response = await fetch('/api/config/public', { cache: 'no-store' });

  if (!response.ok) {
    throw new Error('Não foi possível carregar a configuração do DomnAI.');
  }

  const runtimeConfig = await response.json();
  const { clerkPublishableKey } = runtimeConfig;

  if (!clerkPublishableKey) {
    throw new Error('Chave pública do Clerk não configurada.');
  }

  ReactDOM.createRoot(rootElement).render(
    <ErrorBoundary>
      <ClerkProvider publishableKey={clerkPublishableKey} afterSignOutUrl="/">
        <HashRouter>
          <App />
        </HashRouter>
      </ClerkProvider>
    </ErrorBoundary>,
  );
}

startApplication().catch(renderStartupError);
