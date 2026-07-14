import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';

let domnaiLogoutInProgress = false;

function clearDomnAISessionState() {
  try {
    Object.keys(sessionStorage).forEach((key) => {
      if (key.startsWith('domnai:')) sessionStorage.removeItem(key);
    });
  } catch {
    // O logout continua mesmo quando o armazenamento está indisponível.
  }

  document.documentElement.classList.remove(
    'domnai-gate-pending',
    'domnai-plan-selection-required',
  );
  document.body.classList.remove(
    'domnai-profile-exclusive',
    'domnai-mobile-menu-open',
  );
  window.dispatchEvent(new CustomEvent('domnai:signed-out'));
}

function showDomnAILogoutOverlay() {
  let overlay = document.querySelector('[data-domnai-logout-overlay="true"]');
  if (overlay) return overlay;

  overlay = document.createElement('main');
  overlay.className = 'domnai-user-logout-overlay';
  overlay.dataset.domnaiLogoutOverlay = 'true';
  overlay.setAttribute('aria-busy', 'true');
  overlay.innerHTML = `
    <img src="${DOMNAI_LOGO}" alt="DomnAI">
    <span class="domnai-user-logout-spinner" aria-hidden="true"></span>
  `;
  document.body.appendChild(overlay);
  return overlay;
}

function domnaiSignOut(button) {
  if (domnaiLogoutInProgress) return;
  domnaiLogoutInProgress = true;

  if (button) button.disabled = true;
  showDomnAILogoutOverlay();
  clearDomnAISessionState();

  const landingUrl = `${window.location.origin}${window.location.pathname}?signed_out=${Date.now()}#/`;
  const activeSessionId = window.Clerk?.session?.id;
  let redirected = false;

  const finishRedirect = () => {
    if (redirected) return;
    redirected = true;
    window.location.replace(landingUrl);
  };

  const fallbackTimer = window.setTimeout(finishRedirect, 2200);

  try {
    if (!window.Clerk?.signOut) throw new Error('Sessão não encontrada.');

    const result = window.Clerk.signOut({
      ...(activeSessionId ? { sessionId: activeSessionId } : {}),
      redirectUrl: landingUrl,
    });

    Promise.resolve(result)
      .then(() => {
        window.clearTimeout(fallbackTimer);
        finishRedirect();
      })
      .catch((error) => {
        console.error('Não foi possível encerrar a sessão do DomnAI.', error);
        window.clearTimeout(fallbackTimer);
        finishRedirect();
      });
  } catch (error) {
    console.error('Não foi possível iniciar a saída do DomnAI.', error);
    window.clearTimeout(fallbackTimer);
    finishRedirect();
  }
}

window.domnaiSafeSignOut = () => domnaiSignOut(null);

function removeProfilePageLogout() {
  document.querySelectorAll('[data-domnai-profile-page] .domnai-logout-button')
    .forEach((button) => button.remove());
}

function installSidebarLogout() {
  const sidebar = document.querySelector('.domnai-sidebar');
  const profile = sidebar?.querySelector('.sidebar-profile');
  if (!sidebar || !profile) return;

  let logoutButton = sidebar.querySelector('.domnai-sidebar-logout');
  if (!logoutButton) {
    logoutButton = document.createElement('button');
    logoutButton.type = 'button';
    logoutButton.className = 'domnai-sidebar-logout';
    logoutButton.innerHTML = '<span aria-hidden="true">↪</span><strong>Sair da conta</strong>';
    logoutButton.addEventListener('click', () => domnaiSignOut(logoutButton));
  }

  if (logoutButton.nextElementSibling !== profile) {
    sidebar.insertBefore(logoutButton, profile);
  }
}

function installPlanSelectionLogout() {
  const shell = document.querySelector('.domnai-app-shell.onboarding-plan-mode');
  if (!shell || shell.querySelector('.domnai-plan-logout')) return;

  const logoutButton = document.createElement('button');
  logoutButton.type = 'button';
  logoutButton.className = 'domnai-plan-logout';
  logoutButton.textContent = 'Sair da conta';
  logoutButton.addEventListener('click', () => domnaiSignOut(logoutButton));
  shell.appendChild(logoutButton);
}

function installDomnAILogoutActions() {
  removeProfilePageLogout();
  installSidebarLogout();
  installPlanSelectionLogout();
}

const domnaiLogoutObserver = new MutationObserver(() => {
  window.requestAnimationFrame(installDomnAILogoutActions);
});
domnaiLogoutObserver.observe(document.documentElement, { childList: true, subtree: true });
installDomnAILogoutActions();
