async function domnaiSignOut(button) {
  if (button) {
    button.disabled = true;
    button.textContent = 'Saindo...';
  }

  try {
    if (!window.Clerk?.signOut) throw new Error('Sessão não encontrada.');
    await window.Clerk.signOut({ redirectUrl: `${window.location.origin}/#/` });
  } catch (error) {
    if (button) {
      button.disabled = false;
      button.textContent = 'Sair da conta';
    }
    window.alert(error?.message || 'Não foi possível sair da conta.');
  }
}

function installProfileLogout() {
  const header = document.querySelector('[data-domnai-profile-page] .domnai-profile-header');
  if (!header || header.querySelector('.domnai-profile-header-actions')) return;

  const backButton = header.querySelector('.domnai-profile-close');
  const actions = document.createElement('div');
  actions.className = 'domnai-profile-header-actions';

  if (backButton) actions.appendChild(backButton);

  const logoutButton = document.createElement('button');
  logoutButton.type = 'button';
  logoutButton.className = 'domnai-logout-button';
  logoutButton.textContent = 'Sair da conta';
  logoutButton.addEventListener('click', () => domnaiSignOut(logoutButton));
  actions.appendChild(logoutButton);
  header.appendChild(actions);
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
  installProfileLogout();
  installPlanSelectionLogout();
}

const domnaiLogoutObserver = new MutationObserver(installDomnAILogoutActions);
domnaiLogoutObserver.observe(document.documentElement, { childList: true, subtree: true });
installDomnAILogoutActions();
