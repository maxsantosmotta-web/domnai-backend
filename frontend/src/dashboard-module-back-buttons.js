function requestChatComposerScroll() {
  window.setTimeout(() => {
    window.dispatchEvent(new CustomEvent('domnai-return-to-chat'));
  }, 40);
}

function clickDashboardNow() {
  const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Dashboard'));
  if (dashboardButton) {
    dashboardButton.click();
    requestChatComposerScroll();
    return true;
  }
  window.location.hash = '#/';
  requestChatComposerScroll();
  return false;
}

function ensureCompactBackButton(section, label) {
  if (!section) return;
  const header = section.querySelector(':scope > header');
  if (!header) return;

  if (label === 'Faturamento') {
    const billingButton = header.querySelector('.billing-back-to-chat');
    if (billingButton) {
      billingButton.textContent = 'Voltar';
      billingButton.classList.add('module-back-button');
      billingButton.hidden = false;
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
  if (globalButton) globalButton.style.display = 'none';

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
      originalDashboardButton.textContent = 'Voltar ao Dashboard';
      originalDashboardButton.classList.remove('module-back-button');
      originalDashboardButton.setAttribute('aria-label', 'Voltar ao Dashboard');
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

  const profilePage = button.closest('[data-domnai-profile-page]');
  if (profilePage) {
    const originalDashboardButton = profilePage.querySelector('.domnai-profile-close');
    if (originalDashboardButton) {
      originalDashboardButton.click();
      requestChatComposerScroll();
      return;
    }
  }

  clickDashboardNow();
}, true);

const moduleBackObserver = new MutationObserver(() => window.requestAnimationFrame(applyModuleBackButtons));
moduleBackObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.setTimeout(applyModuleBackButtons, 0));
applyModuleBackButtons();