import React from 'react';
import ReactDOM from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';
import { HashRouter } from 'react-router-dom';
import App from './App';
import ErrorBoundary from './ErrorBoundary';
import './styles.css';
import './scale.css';
import './final-refinement.css';
import './no-glow.css';
import './auth-modal.css';
import './auth-compact.css';
import './dashboard-visual-assets.css';
import './dashboard-final-fixes.css';
import './dashboard-operation-groups.css';
import './dashboard-extra-icons.css';
import './dashboard-billing-enhancements.css';
import './profile-checklist.css';
import './dashboard-onboarding-enhancements.css';
import './dashboard-profile-enhancements.css';
import './dashboard-profile-avatar-sync.css';
import './dashboard-profile-compact.css';
import './dashboard-logout-enhancements.css';
import './dashboard-link-enhancements.js';
import './dashboard-operation-groups.js';
import './dashboard-extra-icons.js';
import './dashboard-billing-enhancements.js';
import './dashboard-onboarding-enhancements.js';
import './dashboard-profile-enhancements.js';
import './dashboard-profile-avatar-sync.js';
import './dashboard-profile-compact.js';
import './dashboard-logout-enhancements.js';
import './dashboard-remove-settings.js';
import './dashboard-error-localization.js';
import './auth-enhancements.js';

const rootElement = document.getElementById('root');

const localization = {
  signIn: {
    start: {
      title: 'Entrar',
      subtitle: '',
      actionText: 'Ainda não tem uma conta?',
      actionLink: 'Criar conta',
    },
  },
  signUp: {
    start: {
      title: 'Criar conta',
      subtitle: '',
      actionText: 'Já possui uma conta?',
      actionLink: 'Fazer login',
    },
  },
  formFieldLabel__emailAddress: 'E-mail',
  formFieldLabel__password: 'Senha',
  formFieldInputPlaceholder__emailAddress: 'Digite seu e-mail',
  formFieldInputPlaceholder__password: 'Digite sua senha',
  formButtonPrimary: 'Continuar',
  dividerText: 'ou',
  socialButtonsBlockButton: 'Continuar com {{provider|titleize}}',
  backButton: 'Voltar',
};

const appearance = {
  layout: {
    socialButtonsPlacement: 'top',
    socialButtonsVariant: 'blockButton',
  },
  variables: {
    colorPrimary: '#d8aa34',
    colorBackground: '#080808',
    colorInputBackground: '#111111',
    colorInputText: '#ffffff',
    colorText: '#ffffff',
    colorTextSecondary: '#a8a8a8',
    colorDanger: '#ff7474',
    borderRadius: '14px',
    fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  },
  elements: {
    modalBackdrop: {
      background: '#050505',
      backdropFilter: 'none',
    },
    modalContent: {
      background: '#050505',
      boxShadow: 'none',
    },
    cardBox: {
      width: 'min(92vw, 420px)',
      boxShadow: 'none',
    },
    card: {
      background: 'linear-gradient(180deg, #101010 0%, #070707 100%)',
      border: '1px solid rgba(216, 170, 52, 0.34)',
      boxShadow: 'none',
      padding: '28px 24px 22px',
    },
    headerTitle: {
      color: '#ffffff',
      fontSize: '1.42rem',
      fontWeight: '700',
      letterSpacing: '-0.02em',
    },
    headerSubtitle: {
      display: 'none',
    },
    socialButtonsBlockButton: {
      minHeight: '48px',
      background: '#151515',
      border: '1px solid rgba(216, 170, 52, 0.38)',
      color: '#ffffff',
      boxShadow: 'none',
    },
    socialButtonsBlockButtonText: {
      color: '#ffffff',
      fontWeight: '600',
    },
    dividerLine: {
      background: 'rgba(216, 170, 52, 0.22)',
    },
    dividerText: {
      color: '#8d8d8d',
    },
    formFieldLabel: {
      color: '#ededed',
      fontWeight: '600',
    },
    formFieldInput: {
      minHeight: '48px',
      background: '#111111',
      border: '1px solid rgba(216, 170, 52, 0.24)',
      color: '#ffffff',
      boxShadow: 'none',
    },
    formButtonPrimary: {
      minHeight: '48px',
      background: 'linear-gradient(135deg, #f1cf69 0%, #d9aa31 55%, #b77b12 100%)',
      color: '#080808',
      fontWeight: '800',
      letterSpacing: '0.06em',
      boxShadow: '0 10px 24px rgba(216, 170, 52, 0.24)',
    },
    footer: {
      background: '#0b0b0b',
      borderTop: '1px solid rgba(216, 170, 52, 0.16)',
    },
    footerActionText: {
      color: '#9d9d9d',
    },
    footerActionLink: {
      color: '#e4bd55',
      fontWeight: '700',
    },
    modalCloseButton: {
      color: '#e8e8e8',
      background: '#151515',
      border: '1px solid rgba(216, 170, 52, 0.28)',
    },
  },
};

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
      <ClerkProvider
        publishableKey={clerkPublishableKey}
        localization={localization}
        appearance={appearance}
        afterSignOutUrl="/#/"
      >
        <HashRouter>
          <App />
        </HashRouter>
      </ClerkProvider>
    </ErrorBoundary>,
  );
}

startApplication().catch(renderStartupError);
