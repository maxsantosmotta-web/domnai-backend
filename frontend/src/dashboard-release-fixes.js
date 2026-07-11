function findSidebarButton(label) {
  return [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes(label));
}

function restoreBillingWhenEmpty() {
  const billingButton = findSidebarButton('Faturamento');
  if (!billingButton?.classList.contains('is-active')) return;

  const section = [...document.querySelectorAll('.internal-section')]
    .find((item) => item.querySelector('header span')?.textContent.trim() === 'Faturamento');
  if (!section) return;

  const hasContent = section.querySelector('.billing-plans-section, .billing-loading-state, .billing-error-state');
  if (hasContent) return;

  section.dataset.billingConnected = 'false';
  window.dispatchEvent(new HashChangeEvent('hashchange'));
}

function softenFreePlanCopy() {
  document.querySelectorAll('body *').forEach((element) => {
    if (element.children.length) return;
    const text = element.textContent.trim();

    if (text === 'Chat disponível no plano PREMIUM') {
      element.remove();
      return;
    }

    if (text === 'Este recurso não está disponível no plano FREE') {
      element.textContent = 'Este recurso faz parte do plano PREMIUM';
      return;
    }

    if (text === 'Assine o PREMIUM para utilizar operações, chat, arquivos, Biblioteca e Lixeira.') {
      element.textContent = 'Conheça o plano PREMIUM para acessar operações, chat, arquivos, Biblioteca e Lixeira.';
    }

    if (text === 'Continuar no FREE') {
      element.textContent = 'Voltar';
    }

    if (text === 'Ver plano PREMIUM') {
      element.textContent = 'Conhecer PREMIUM';
    }
  });
}

function keepLogoutInsideProfileOnly() {
  const profileOpen = Boolean(document.querySelector('[data-domnai-profile-page]'));
  document.querySelectorAll('.global-exit-button, .domnai-plan-logout').forEach((button) => {
    button.style.display = profileOpen ? '' : 'none';
  });
}

function repairDashboardVisualState() {
  const dashboardButton = findSidebarButton('Dashboard');
  if (dashboardButton?.classList.contains('is-active')) {
    document.documentElement.classList.add('domnai-dashboard-active');
  } else {
    document.documentElement.classList.remove('domnai-dashboard-active');
  }
}

function applyReleaseFixes() {
  restoreBillingWhenEmpty();
  softenFreePlanCopy();
  keepLogoutInsideProfileOnly();
  repairDashboardVisualState();
}

const releaseFixObserver = new MutationObserver(() => window.requestAnimationFrame(applyReleaseFixes));
releaseFixObserver.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
window.addEventListener('hashchange', () => window.setTimeout(applyReleaseFixes, 80));
window.addEventListener('focus', () => window.setTimeout(applyReleaseFixes, 80));
window.setInterval(applyReleaseFixes, 1200);
applyReleaseFixes();
