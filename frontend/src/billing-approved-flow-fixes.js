import './billing-approved-flow-fixes.css';

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

function closeProfileForm(overlay) {
  if (!overlay?.isConnected) return;
  overlay.remove();
}

function applyApprovedBillingDetails() {
  const billingBack = document.querySelector('[data-billing-action="back-to-chat"]');
  if (billingBack) {
    billingBack.textContent = 'Voltar';
    billingBack.setAttribute('aria-label', 'Voltar');
    billingBack.classList.add('billing-approved-back');
  }

  const overlay = document.querySelector('.profile-checklist-overlay');
  const header = overlay?.querySelector('.profile-checklist-card > header');
  if (overlay && header && !header.querySelector('.profile-checklist-top-cancel')) {
    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.className = 'profile-checklist-top-cancel';
    cancelButton.textContent = 'Cancelar';
    cancelButton.setAttribute('aria-label', 'Cancelar cadastro');
    cancelButton.addEventListener('click', () => closeProfileForm(overlay));
    header.appendChild(cancelButton);
  }

  keepBillingSelected();
}

document.addEventListener('click', (event) => {
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

const approvedBillingObserver = new MutationObserver(applyApprovedBillingDetails);
approvedBillingObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('domnai:billing-updated', () => window.requestAnimationFrame(applyApprovedBillingDetails));
window.addEventListener('pageshow', () => window.requestAnimationFrame(applyApprovedBillingDetails));
applyApprovedBillingDetails();
