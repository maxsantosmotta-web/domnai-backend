const DOMNAI_BILLING_CACHE_PREFIX = 'domnai:billing-html:v1:';

function clearLegacyBillingHtmlCache() {
  try {
    Object.keys(sessionStorage)
      .filter((key) => key.startsWith(DOMNAI_BILLING_CACHE_PREFIX))
      .forEach((key) => sessionStorage.removeItem(key));
  } catch {
    // Sem impacto funcional.
  }
}

function findSidebarButton(label) {
  return [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes(label));
}

function findBillingSection() {
  return [...document.querySelectorAll('.internal-section')]
    .find((item) => item.querySelector('header span')?.textContent.trim() === 'Faturamento'
      || item.querySelector('.billing-loading-state, .billing-page-header'));
}

function restoreBillingWhenEmpty() {
  const billingButton = findSidebarButton('Faturamento');
  if (!billingButton?.classList.contains('is-active')) return;

  const section = findBillingSection();
  if (!section) return;

  const hasContent = section.querySelector('.billing-plans-section, .billing-loading-state, .billing-error-state');
  if (hasContent) return;

  section.dataset.billingConnected = 'false';
  window.dispatchEvent(new HashChangeEvent('hashchange'));
}

function softenFreePlanCopy(root = document) {
  root.querySelectorAll?.('body *, *').forEach((element) => {
    if (element.children.length) return;
    const text = element.textContent.trim();

    if (text === 'Chat disponível no plano PREMIUM') {
      element.style.display = 'none';
      return;
    }

    if (text === 'Este recurso não está disponível no plano FREE') {
      element.textContent = 'Este recurso faz parte do plano PREMIUM';
      return;
    }

    if (text === 'Assine o PREMIUM para utilizar operações, chat, arquivos, Biblioteca e Lixeira.') {
      element.textContent = 'Conheça o plano PREMIUM para acessar operações, chat, arquivos, Biblioteca e Lixeira.';
    }

    if (text === 'Continuar no FREE') element.textContent = 'Voltar';
    if (text === 'Ver plano PREMIUM') element.textContent = 'Conhecer PREMIUM';
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
  document.documentElement.classList.toggle('domnai-dashboard-active', Boolean(dashboardButton?.classList.contains('is-active')));
}

function applyReleaseFixes(root = document) {
  restoreBillingWhenEmpty();
  softenFreePlanCopy(root);
  keepLogoutInsideProfileOnly();
  repairDashboardVisualState();
}

let releaseFixFrame = 0;
const releaseFixObserver = new MutationObserver((mutations) => {
  if (releaseFixFrame) return;
  releaseFixFrame = window.requestAnimationFrame(() => {
    releaseFixFrame = 0;
    const addedRoot = mutations.flatMap((mutation) => [...mutation.addedNodes])
      .find((node) => node.nodeType === Node.ELEMENT_NODE) || document;
    applyReleaseFixes(addedRoot);
  });
});

clearLegacyBillingHtmlCache();
releaseFixObserver.observe(document.body || document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.requestAnimationFrame(() => applyReleaseFixes()));
window.addEventListener('pageshow', () => window.requestAnimationFrame(() => applyReleaseFixes()));
applyReleaseFixes();
