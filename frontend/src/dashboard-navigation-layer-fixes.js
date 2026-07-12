function navText(button) {
  return String(button?.textContent || '').replace(/\s+/g, ' ').trim();
}

function activeNavigationLabel() {
  const active = [...document.querySelectorAll('.sidebar-navigation button.is-active, .sidebar-system-group button.is-active')][0];
  return navText(active);
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

function hideTemporaryLogoutButtons() {
  document.querySelectorAll('.domnai-context-logout, .domnai-plan-logout, .global-exit-button').forEach((button) => {
    button.classList.add('domnai-hidden-exit');
    button.setAttribute('aria-hidden', 'true');
    button.setAttribute('tabindex', '-1');
  });
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

function syncContextControls() {
  const profileOpen = Boolean(document.querySelector('[data-domnai-profile-page]'));
  const checklistOpen = Boolean(document.querySelector('.profile-checklist-overlay'));
  const label = activeNavigationLabel();
  const systemPage = ['Faturamento', 'Biblioteca', 'Lixeira'].some((name) => label.includes(name));
  const chatContext = !profileOpen && !checklistOpen && !systemPage;

  document.body.classList.toggle('domnai-profile-exclusive', profileOpen);
  document.body.classList.toggle('domnai-checklist-exclusive', checklistOpen);
  document.body.classList.toggle('domnai-chat-context', chatContext);
  document.body.classList.toggle('domnai-system-context', systemPage);

  if (profileOpen || checklistOpen) closeMobileSidebar();
  hideTemporaryLogoutButtons();
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

function keepDashboardOpenWhenAlreadyActive(event) {
  const dashboardButton = event.target.closest('.sidebar-navigation button');
  if (!dashboardButton) return false;
  if (!navText(dashboardButton).includes('Dashboard')) return false;
  if (!dashboardButton.classList.contains('is-active')) return false;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  return true;
}

function restoreVisibleAppAfterReturn() {
  if (document.visibilityState && document.visibilityState !== 'visible') return;
  if (document.documentElement.classList.contains('domnai-plan-selection-required')) return;
  if (!document.querySelector('.domnai-app-shell')) return;
  document.documentElement.classList.remove('domnai-gate-pending');
}

function handleNavigationClick(event) {
  if (keepDashboardOpenWhenAlreadyActive(event)) return;

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
      syncContextControls();
    }, 0);
    return;
  }

  const navigationButton = event.target.closest('.sidebar-navigation button, .sidebar-system-group button');
  if (!navigationButton) return;
  window.setTimeout(() => {
    closeMobileSidebar();
    syncContextControls();
  }, 0);
}

document.addEventListener('click', handleNavigationClick, true);

const navigationLayerObserver = new MutationObserver(() => {
  window.requestAnimationFrame(() => {
    syncContextControls();
    softenPremiumGate();
  });
});

navigationLayerObserver.observe(document.documentElement, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['class', 'aria-hidden', 'style'] });
window.addEventListener('hashchange', () => window.setTimeout(syncContextControls, 50));
window.addEventListener('focus', () => {
  restoreVisibleAppAfterReturn();
  window.setTimeout(syncContextControls, 50);
});
window.addEventListener('pageshow', restoreVisibleAppAfterReturn);
document.addEventListener('visibilitychange', restoreVisibleAppAfterReturn);
window.addEventListener('resize', syncMobileMenuScrollLock);
window.setInterval(syncContextControls, 1000);
syncContextControls();
softenPremiumGate();
restoreVisibleAppAfterReturn();
