import './billing-approved-flow-safe.css';

function planAccessReady() {
  const status = window.__domnaiBillingStatus;
  return Boolean(
    status?.profileCompleted
    && status?.plan
    && !['unselected', 'free_demo'].includes(status.plan),
  );
}

function findBillingButton() {
  return [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Faturamento'));
}

function keepBillingSelected() {
  if (planAccessReady()) return;
  const billingButton = findBillingButton();
  if (billingButton && !billingButton.classList.contains('is-active')) {
    billingButton.click();
  }
}

async function signOutFromPlanFlow(button) {
  if (button) {
    button.disabled = true;
    button.textContent = 'Saindo...';
  }

  try {
    if (typeof window.domnaiSafeSignOut !== 'function') throw new Error('Sessão não encontrada.');
    await window.domnaiSafeSignOut();
  } catch (error) {
    if (button) {
      button.disabled = false;
      button.textContent = 'Sair da conta';
    }
    window.alert(error?.message || 'Não foi possível sair da conta.');
  }
}

function decorateBillingSignOutButton() {
  const button = document.querySelector('[data-billing-action="back-to-chat"]');
  if (!button || button.dataset.approvedBillingBack === 'true') return;

  button.dataset.approvedBillingBack = 'true';
  button.textContent = 'Sair da conta';
  button.setAttribute('aria-label', 'Sair da conta');
  button.classList.add('billing-approved-back');
}

function addProfileTopSignOut() {
  const overlay = document.querySelector('.profile-checklist-overlay');
  const header = overlay?.querySelector('.profile-checklist-card > header');
  if (!overlay || !header || header.querySelector('.profile-checklist-top-cancel')) return;

  const logoutButton = document.createElement('button');
  logoutButton.type = 'button';
  logoutButton.className = 'profile-checklist-top-cancel';
  logoutButton.textContent = 'Sair da conta';
  logoutButton.setAttribute('aria-label', 'Sair da conta');
  logoutButton.addEventListener('click', () => signOutFromPlanFlow(logoutButton));
  header.appendChild(logoutButton);
}

function applyApprovedDetails() {
  decorateBillingSignOutButton();
  addProfileTopSignOut();
  keepBillingSelected();
}

const scheduledDelays = [0, 60, 160, 350, 700, 1200, 2200, 4000, 7000];
function scheduleApprovedDetails() {
  scheduledDelays.forEach((delay) => window.setTimeout(applyApprovedDetails, delay));
}

document.addEventListener('click', (event) => {
  const freeButton = event.target.closest?.('[data-billing-action="free"]');
  if (freeButton) scheduleApprovedDetails();

  const billingSignOut = event.target.closest?.('[data-billing-action="back-to-chat"]');
  if (billingSignOut && !planAccessReady()) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    signOutFromPlanFlow(billingSignOut);
    return;
  }

  if (planAccessReady()) return;

  const navigationButton = event.target.closest?.('.sidebar-navigation button');
  if (navigationButton && !navigationButton.textContent.trim().includes('Faturamento')) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    keepBillingSelected();
  }
}, true);

window.addEventListener('domnai:billing-updated', scheduleApprovedDetails);
window.addEventListener('pageshow', scheduleApprovedDetails);
window.addEventListener('hashchange', scheduleApprovedDetails);
scheduleApprovedDetails();
