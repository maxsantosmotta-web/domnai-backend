const DOMNAI_BILLING_CACHE_PREFIX = 'domnai:billing-html:v1:';
let domnaiHydratedBillingHtml = '';

function findSidebarButton(label) {
  return [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes(label));
}

function billingCacheKey() {
  const userId = window.Clerk?.user?.id;
  return userId ? `${DOMNAI_BILLING_CACHE_PREFIX}${userId}` : '';
}

function readBillingCache() {
  const key = billingCacheKey();
  if (!key) return '';
  try {
    return sessionStorage.getItem(key) || '';
  } catch {
    return '';
  }
}

function writeBillingCache(html) {
  const key = billingCacheKey();
  if (!key || !html) return;
  try {
    sessionStorage.setItem(key, html);
  } catch {
    // Cache é apenas uma otimização visual.
  }
}

function clearBillingCache() {
  const key = billingCacheKey();
  if (!key) return;
  try {
    sessionStorage.removeItem(key);
  } catch {
    // Sem impacto funcional.
  }
  domnaiHydratedBillingHtml = '';
}

function findBillingSection() {
  return [...document.querySelectorAll('.internal-section')]
    .find((item) => item.querySelector('header span')?.textContent.trim() === 'Faturamento'
      || item.querySelector('.billing-loading-state, .billing-page-header'));
}

function hydrateBillingFromCache() {
  const section = findBillingSection();
  if (!section?.querySelector('.billing-loading-state')) return;

  const cachedHtml = readBillingCache();
  if (!cachedHtml) return;

  domnaiHydratedBillingHtml = cachedHtml;
  section.innerHTML = cachedHtml;
  section.dataset.billingCachePreview = 'true';
}

function cacheRenderedBilling() {
  const section = findBillingSection();
  if (!section?.querySelector('.billing-page-header, .billing-plans-section')) return;
  if (section.querySelector('.billing-loading-state, .billing-error-state')) return;

  const html = section.innerHTML;
  if (section.dataset.billingCachePreview === 'true' && html === domnaiHydratedBillingHtml) return;

  writeBillingCache(html);
  section.dataset.billingCachePreview = 'false';
  domnaiHydratedBillingHtml = '';
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
  hydrateBillingFromCache();
  cacheRenderedBilling();
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

releaseFixObserver.observe(document.body || document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.requestAnimationFrame(() => applyReleaseFixes()));
window.addEventListener('domnai:billing-updated', clearBillingCache);
window.addEventListener('pageshow', () => window.requestAnimationFrame(() => applyReleaseFixes()));
applyReleaseFixes();
