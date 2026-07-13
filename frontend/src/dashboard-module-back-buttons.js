function requestChatComposerScroll() {
  window.setTimeout(() => {
    window.dispatchEvent(new CustomEvent('domnai-return-to-chat'));
  }, 40);
}

function clickDashboardNow({ scrollToChat = true } = {}) {
  const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Dashboard'));
  if (dashboardButton) {
    dashboardButton.click();
    if (scrollToChat) requestChatComposerScroll();
    return true;
  }
  window.location.hash = '#/';
  if (scrollToChat) requestChatComposerScroll();
  return false;
}

function planIsReady() {
  const status = window.__domnaiBillingStatus;
  return Boolean(status?.plan && !['unselected', 'free_demo'].includes(status.plan));
}

function ensureCompactBackButton(section, label) {
  if (!section) return;
  const header = section.querySelector(':scope > header');
  if (!header) return;

  if (label === 'Faturamento') {
    const billingButton = header.querySelector('.billing-back-to-chat');
    if (billingButton) {
      if (billingButton.textContent.trim() !== 'Voltar') billingButton.textContent = 'Voltar';
      if (!billingButton.classList.contains('module-back-button')) {
        billingButton.classList.add('module-back-button');
      }
      return;
    }
  }

  if (header.querySelector('.module-back-button')) return;

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'module-back-button';
  button.textContent = 'Voltar';
  button.setAttribute('aria-label', `Voltar ao chat a partir de ${label}`);
  header.appendChild(button);
}

function renderImmediateBillingShell(section) {
  if (!section.querySelector('.billing-loading-state')) return;

  section.innerHTML = `
    <header class="billing-page-header">
      <div>
        <span>Faturamento</span>
        <h1>Plano e créditos</h1>
        <p>Acompanhe seu saldo, assinatura e pacotes adicionais.</p>
      </div>
      <button type="button" class="billing-back-to-chat module-back-button" aria-label="Voltar ao chat">Voltar</button>
    </header>
    <div class="billing-quiet-loading" aria-hidden="true">
      <div></div><div></div><div></div>
    </div>
  `;
}

function applyModuleBackButtons() {
  const globalButton = document.querySelector('.global-exit-button');
  if (globalButton && globalButton.style.display !== 'none') globalButton.style.display = 'none';

  document.querySelectorAll('.internal-section').forEach((section) => {
    let label = section.querySelector(':scope > header span')?.textContent.trim();
    if (!label && section.querySelector('.billing-loading-state')) label = 'Faturamento';

    if (label === 'Faturamento') renderImmediateBillingShell(section);
    if (['Biblioteca', 'Lixeira', 'Faturamento'].includes(label)) {
      ensureCompactBackButton(section, label);
    }
  });

  const profilePage = document.querySelector('[data-domnai-profile-page]');
  if (profilePage) {
    const originalDashboardButton = profilePage.querySelector('.domnai-profile-close');
    if (originalDashboardButton) {
      if (originalDashboardButton.textContent.trim() !== 'Voltar ao Dashboard') {
        originalDashboardButton.textContent = 'Voltar ao Dashboard';
      }
      originalDashboardButton.classList.remove('module-back-button');
      originalDashboardButton.setAttribute('aria-label', 'Voltar ao Dashboard');
      originalDashboardButton.dataset.profileDestination = 'dashboard';
    }
    ensureCompactBackButton(profilePage, 'Perfil');
  }
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('.module-back-button');
  if (!button) return;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();

  const checklistOverlay = document.querySelector('.profile-checklist-overlay');
  if (checklistOverlay) {
    const checklistBack = checklistOverlay.querySelector('.profile-checklist-cancel');
    if (checklistBack) checklistBack.click();
    return;
  }

  const profilePage = button.closest('[data-domnai-profile-page]');
  if (profilePage) {
    document.body.classList.remove('domnai-profile-exclusive', 'domnai-mobile-menu-open');
    document.querySelector('.domnai-main-area')?.classList.remove('profile-page-open');
    profilePage.remove();
    clickDashboardNow({ scrollToChat: true });
    return;
  }

  if (button.closest('.billing-page-header') && !planIsReady()) return;
  clickDashboardNow({ scrollToChat: true });
}, true);

const moduleBackObserver = new MutationObserver(() => window.requestAnimationFrame(applyModuleBackButtons));
moduleBackObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.setTimeout(applyModuleBackButtons, 0));
applyModuleBackButtons();
