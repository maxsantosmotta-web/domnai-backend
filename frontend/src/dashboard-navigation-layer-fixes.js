function navText(button) {
  return String(button?.textContent || '').replace(/\s+/g, ' ').trim();
}

function closeMobileSidebar() {
  const sidebar = document.querySelector('.domnai-sidebar');
  if (!sidebar) return;

  const closeButton = [...sidebar.querySelectorAll('button')].find((button) => {
    const aria = String(button.getAttribute('aria-label') || '').toLowerCase();
    const title = String(button.getAttribute('title') || '').toLowerCase();
    const text = navText(button);
    return aria.includes('fechar') || title.includes('fechar') || text === '×' || text === '✕' || text === 'X';
  });

  if (closeButton) closeButton.click();
  sidebar.classList.remove('is-open', 'open', 'active', 'visible');
  document.querySelectorAll('.sidebar-backdrop').forEach((backdrop) => backdrop.classList.remove('is-visible', 'visible', 'active'));
  document.body.classList.remove('domnai-mobile-menu-open');
}

function removeTemporaryLogoutButtons() {
  document.querySelectorAll('.domnai-context-logout, .domnai-plan-logout, .global-exit-button').forEach((button) => button.remove());
}

function detectMobileMenuState() {
  const sidebar = document.querySelector('.domnai-sidebar');
  const backdrop = document.querySelector('.sidebar-backdrop');
  if (!sidebar) return false;

  const classOpen = ['is-open', 'open', 'active', 'visible'].some((name) => sidebar.classList.contains(name));
  const backdropOpen = backdrop && ['is-visible', 'visible', 'active'].some((name) => backdrop.classList.contains(name));
  const ariaOpen = sidebar.getAttribute('aria-hidden') === 'false';
  const style = window.getComputedStyle(sidebar);
  const mobile = window.matchMedia('(max-width: 820px)').matches;
  const visibleByStyle = mobile && style.display !== 'none' && style.visibility !== 'hidden' && style.transform === 'none';

  return mobile && (classOpen || backdropOpen || ariaOpen || visibleByStyle);
}

function syncMobileMenuScrollLock() {
  document.body.classList.toggle('domnai-mobile-menu-open', detectMobileMenuState());
}

function enforceExclusiveLayers() {
  const profileOpen = Boolean(document.querySelector('[data-domnai-profile-page]'));
  const checklistOpen = Boolean(document.querySelector('.profile-checklist-overlay'));
  document.body.classList.toggle('domnai-profile-exclusive', profileOpen);
  document.body.classList.toggle('domnai-checklist-exclusive', checklistOpen);

  if (profileOpen || checklistOpen) closeMobileSidebar();
  removeTemporaryLogoutButtons();
  syncMobileMenuScrollLock();
}

function softenPremiumGate() {
  const all = [...document.querySelectorAll('body *')];
  const title = all.find((element) => {
    if (element.children.length) return false;
    const text = navText(element);
    return text === 'Este recurso faz parte do plano PREMIUM' || text === 'Este recurso não está disponível no plano FREE';
  });
  if (!title) return;

  const gate = title.closest('[role="dialog"]') || title.closest('section') || title.parentElement?.parentElement;
  if (!gate || gate.dataset.softPremiumGate === 'true') return;
  gate.dataset.softPremiumGate = 'true';
  gate.classList.add('domnai-premium-gate-soft');

  const eyebrow = [...gate.querySelectorAll('*')].find((element) => !element.children.length && navText(element) === 'RECURSO PREMIUM');
  if (eyebrow) eyebrow.textContent = 'ACESSO PREMIUM';
  title.textContent = 'Disponível no PREMIUM';

  const paragraph = [...gate.querySelectorAll('p, div, span')].find((element) => {
    if (element.children.length) return false;
    const text = navText(element);
    return text.includes('Conheça o plano PREMIUM') || text.includes('Assine o PREMIUM');
  });
  if (paragraph) paragraph.textContent = 'Este recurso faz parte do acesso completo.';

  const buttons = [...gate.querySelectorAll('button')];
  if (buttons[0]) buttons[0].textContent = 'Agora não';
  if (buttons[1]) buttons[1].textContent = 'Ver PREMIUM';
}

function handleNavigationClick(event) {
  const menuButton = event.target.closest('.mobile-menu-button');
  if (menuButton) {
    window.setTimeout(syncMobileMenuScrollLock, 20);
    return;
  }

  if (event.target.closest('.sidebar-backdrop')) {
    window.setTimeout(() => document.body.classList.remove('domnai-mobile-menu-open'), 0);
    return;
  }

  const profile = event.target.closest('.domnai-profile-trigger, .sidebar-profile');
  if (profile) {
    window.setTimeout(() => {
      closeMobileSidebar();
      enforceExclusiveLayers();
    }, 0);
    return;
  }

  const navigationButton = event.target.closest('.sidebar-navigation button, .sidebar-system-group button');
  if (!navigationButton) return;
  window.setTimeout(() => {
    closeMobileSidebar();
    enforceExclusiveLayers();
  }, 0);
}

document.addEventListener('click', handleNavigationClick, true);

const navigationLayerObserver = new MutationObserver(() => {
  window.requestAnimationFrame(() => {
    enforceExclusiveLayers();
    softenPremiumGate();
  });
});

navigationLayerObserver.observe(document.documentElement, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class', 'aria-hidden', 'style'] });
window.addEventListener('hashchange', () => window.setTimeout(enforceExclusiveLayers, 50));
window.addEventListener('focus', () => window.setTimeout(enforceExclusiveLayers, 50));
window.addEventListener('resize', syncMobileMenuScrollLock);
window.setInterval(enforceExclusiveLayers, 1000);
enforceExclusiveLayers();
softenPremiumGate();
