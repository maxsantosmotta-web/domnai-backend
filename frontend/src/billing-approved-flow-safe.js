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

function decorateBillingBackButton() {
  const button = document.querySelector('[data-billing-action="back-to-chat"]');
  if (!button || button.dataset.approvedBillingBack === 'true') return;

  button.dataset.approvedBillingBack = 'true';
  button.textContent = 'Voltar';
  button.setAttribute('aria-label', 'Voltar');
  button.classList.add('billing-approved-back');
}

function addProfileTopCancel() {
  const overlay = document.querySelector('.profile-checklist-overlay');
  const header = overlay?.querySelector('.profile-checklist-card > header');
  if (!overlay || !header || header.querySelector('.profile-checklist-top-cancel')) return;

  const cancelButton = document.createElement('button');
  cancelButton.type = 'button';
  cancelButton.className = 'profile-checklist-top-cancel';
  cancelButton.textContent = 'Cancelar';
  cancelButton.setAttribute('aria-label', 'Cancelar cadastro');
  cancelButton.addEventListener('click', () => {
    const lowerBack = overlay.querySelector('.profile-checklist-cancel');
    if (lowerBack) lowerBack.click();
    else overlay.remove();
  });
  header.appendChild(cancelButton);
}

function applyApprovedDetails() {
  decorateBillingBackButton();
  addProfileTopCancel();
  keepBillingSelected();
}

const scheduledDelays = [0, 60, 160, 350, 700, 1200, 2200, 4000, 7000];
function scheduleApprovedDetails() {
  scheduledDelays.forEach((delay) => window.setTimeout(applyApprovedDetails, delay));
}

document.addEventListener('click', (event) => {
  const freeButton = event.target.closest?.('[data-billing-action="free"]');
  if (freeButton) scheduleApprovedDetails();

  if (planAccessReady()) return;

  const navigationButton = event.target.closest?.('.sidebar-navigation button');
  if (navigationButton && !navigationButton.textContent.trim().includes('Faturamento')) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    keepBillingSelected();
    return;
  }

  const billingBack = event.target.closest?.('[data-billing-action="back-to-chat"]');
  if (billingBack) {
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
