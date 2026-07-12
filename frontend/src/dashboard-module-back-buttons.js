function returnToDashboard() {
  const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Dashboard'));
  if (dashboardButton) {
    dashboardButton.click();
    return;
  }
  window.location.hash = '#/';
}

function ensureModuleBackButton(section, label) {
  if (!section) return;
  const header = section.querySelector(':scope > header');
  if (!header) return;

  let button = header.querySelector('.module-back-button:not(.domnai-profile-close)');
  if (!button) {
    button = document.createElement('button');
    button.type = 'button';
    button.className = 'module-back-button';
    button.textContent = 'Voltar';
    button.setAttribute('aria-label', `Voltar ao chat a partir de ${label}`);
    button.addEventListener('click', returnToDashboard);
    header.appendChild(button);
  }
}

function applyModuleBackButtons() {
  const globalButton = document.querySelector('.global-exit-button');
  if (globalButton) globalButton.style.display = 'none';

  document.querySelectorAll('.internal-section').forEach((section) => {
    const label = section.querySelector(':scope > header span')?.textContent.trim();
    if (['Biblioteca', 'Lixeira', 'Faturamento'].includes(label)) {
      ensureModuleBackButton(section, label);
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
    ensureModuleBackButton(profilePage, 'Perfil');
  }

  const billingButton = document.querySelector('.billing-back-to-chat');
  if (billingButton) {
    billingButton.textContent = 'Voltar';
    billingButton.classList.add('module-back-button');
    billingButton.hidden = false;
    billingButton.style.display = '';
  }
}

const moduleBackObserver = new MutationObserver(() => window.requestAnimationFrame(applyModuleBackButtons));
moduleBackObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.setTimeout(applyModuleBackButtons, 50));
applyModuleBackButtons();
