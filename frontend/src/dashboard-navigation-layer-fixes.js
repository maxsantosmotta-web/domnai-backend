function navText(button) {
  return String(button?.textContent || '').replace(/\s+/g, ' ').trim();
}

function activeSystemPage() {
  const active = [...document.querySelectorAll('.sidebar-navigation button.is-active, .sidebar-system-group button.is-active')][0];
  const label = navText(active);
  if (label.includes('Faturamento')) return 'billing';
  if (label.includes('Biblioteca')) return 'library';
  if (label.includes('Lixeira')) return 'trash';
  if (label.includes('Dashboard')) return 'dashboard';
  return '';
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
}

async function safeSignOut(button) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = 'Saindo...';
  try {
    await window.Clerk?.signOut?.({ redirectUrl: `${window.location.origin}/#/` });
  } catch (error) {
    button.disabled = false;
    button.textContent = original;
    window.alert(error?.message || 'Não foi possível sair da conta.');
  }
}

function installContextLogout() {
  const profileOpen = Boolean(document.querySelector('[data-domnai-profile-page]'));
  const page = activeSystemPage();
  const allowed = profileOpen || ['billing', 'library', 'trash'].includes(page);
  let button = document.querySelector('.domnai-context-logout');

  if (!allowed) {
    button?.remove();
    return;
  }

  if (!button) {
    button = document.createElement('button');
    button.type = 'button';
    button.className = 'domnai-context-logout';
    button.textContent = 'Sair da conta';
    button.addEventListener('click', () => safeSignOut(button));
    document.body.appendChild(button);
  }
}

function enforceExclusiveLayers() {
  const profileOpen = Boolean(document.querySelector('[data-domnai-profile-page]'));
  const checklistOpen = Boolean(document.querySelector('.profile-checklist-overlay'));
  document.body.classList.toggle('domnai-profile-exclusive', profileOpen);
  document.body.classList.toggle('domnai-checklist-exclusive', checklistOpen);

  if (profileOpen || checklistOpen) closeMobileSidebar();
  installContextLogout();
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

navigationLayerObserver.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
window.addEventListener('hashchange', () => window.setTimeout(enforceExclusiveLayers, 50));
window.addEventListener('focus', () => window.setTimeout(enforceExclusiveLayers, 50));
window.setInterval(enforceExclusiveLayers, 1000);
enforceExclusiveLayers();
softenPremiumGate();
