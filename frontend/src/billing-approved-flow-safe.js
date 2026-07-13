import './billing-approved-flow-safe.css';

function decorateBillingBackButton() {
  const button = document.querySelector('[data-billing-action="back-to-chat"]');
  if (!button || button.dataset.approvedBillingBack === 'true') return;

  button.dataset.approvedBillingBack = 'true';
  button.textContent = 'Voltar';
  button.setAttribute('aria-label', 'Voltar ao Dashboard');
  button.classList.add('billing-approved-back');
}

function addProfileTopLogout() {
  const overlay = document.querySelector('.profile-checklist-overlay');
  const header = overlay?.querySelector('.profile-checklist-card > header');
  if (!overlay || !header || header.querySelector('.profile-checklist-top-cancel')) return;

  const logoutButton = document.createElement('button');
  logoutButton.type = 'button';
  logoutButton.className = 'profile-checklist-top-cancel';
  logoutButton.textContent = 'Sair da conta';
  logoutButton.setAttribute('aria-label', 'Sair da conta');
  logoutButton.addEventListener('click', async () => {
    logoutButton.disabled = true;
    logoutButton.textContent = 'Saindo...';
    try {
      if (typeof window.domnaiSafeSignOut !== 'function') throw new Error('Sessão não encontrada.');
      await window.domnaiSafeSignOut();
    } catch (error) {
      logoutButton.disabled = false;
      logoutButton.textContent = 'Sair da conta';
      window.alert(error?.message || 'Não foi possível sair da conta.');
    }
  });
  header.appendChild(logoutButton);
}

function applyApprovedDetails() {
  decorateBillingBackButton();
  addProfileTopLogout();
}

const scheduledDelays = [0, 60, 160, 350, 700, 1200, 2200, 4000, 7000];
function scheduleApprovedDetails() {
  scheduledDelays.forEach((delay) => window.setTimeout(applyApprovedDetails, delay));
}

document.addEventListener('click', (event) => {
  const freeButton = event.target.closest?.('[data-billing-action="free"]');
  if (freeButton) scheduleApprovedDetails();
}, true);

window.addEventListener('domnai:billing-updated', scheduleApprovedDetails);
window.addEventListener('pageshow', scheduleApprovedDetails);
window.addEventListener('hashchange', scheduleApprovedDetails);
scheduleApprovedDetails();
