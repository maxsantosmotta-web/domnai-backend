let flowStabilityBusy = false;

async function flowAuthToken() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session.getToken();
    if (window.Clerk?.loaded && !window.Clerk.session) return null;
    await new Promise((resolve) => window.setTimeout(resolve, 100));
  }
  return null;
}

async function refreshBillingStatusAndNotify() {
  if (flowStabilityBusy) return window.__domnaiBillingStatus || null;
  if (document.querySelector('.profile-checklist-overlay')) return window.__domnaiBillingStatus || null;

  flowStabilityBusy = true;
  try {
    const token = await flowAuthToken();
    if (!token) return null;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch('/api/billing/status', {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
        signal: controller.signal,
      });
      if (!response.ok) return null;
      const status = await response.json();
      window.__domnaiBillingStatus = status;
      window.dispatchEvent(new CustomEvent('domnai:billing-updated', { detail: status }));
      return status;
    } finally {
      window.clearTimeout(timeout);
    }
  } catch (error) {
    console.error('[DomnAI] Falha ao atualizar status de faturamento:', error);
    return null;
  } finally {
    flowStabilityBusy = false;
  }
}

function planIsSelected(status = window.__domnaiBillingStatus) {
  return Boolean(status?.plan && !['unselected', 'free_demo'].includes(status.plan));
}

function openDashboardSafely() {
  const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Dashboard'));
  if (dashboardButton) {
    dashboardButton.click();
    return;
  }
  window.location.hash = '#/';
}

function enhanceBillingFailureState() {
  const errorState = document.querySelector('.billing-error-state');
  if (!errorState || errorState.dataset.flowFixed === 'true') return;
  errorState.dataset.flowFixed = 'true';

  const retry = errorState.querySelector('button');
  retry?.addEventListener('click', () => {
    retry.disabled = true;
    window.setTimeout(() => { retry.disabled = false; }, 2500);
  });

  if (planIsSelected()) {
    const back = document.createElement('button');
    back.type = 'button';
    back.className = 'billing-recovery-back';
    back.textContent = 'Voltar ao painel';
    back.addEventListener('click', openDashboardSafely);
    errorState.appendChild(back);
  } else {
    const logout = document.createElement('button');
    logout.type = 'button';
    logout.className = 'billing-recovery-logout';
    logout.textContent = 'Sair da conta';
    logout.addEventListener('click', () => window.domnaiSafeSignOut?.());
    errorState.appendChild(logout);
  }
}

function stabilizeProfileBackButton() {
  document.querySelectorAll('.domnai-profile-close:not([data-flow-fixed]), .domnai-profile-cancel:not([data-flow-fixed])').forEach((button) => {
    button.dataset.flowFixed = 'true';
    button.addEventListener('click', () => {
      window.setTimeout(() => {
        if (planIsSelected()) openDashboardSafely();
      }, 60);
    });
  });
}

function applyFlowStabilityFixes() {
  stabilizeProfileBackButton();
  enhanceBillingFailureState();
}

document.addEventListener('click', (event) => {
  const button = event.target.closest?.('.profile-checklist-cancel');
  if (!button || button.dataset.stableBackTransition === 'running') return;

  const overlay = button.closest('.profile-checklist-overlay');
  if (!overlay) return;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  button.dataset.stableBackTransition = 'running';

  window.dispatchEvent(new CustomEvent('domnai:onboarding-profile-cancelled'));
  window.requestAnimationFrame(() => {
    overlay.remove();
  });
}, true);

const flowStabilityObserver = new MutationObserver(() => window.requestAnimationFrame(applyFlowStabilityFixes));
flowStabilityObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('pageshow', () => refreshBillingStatusAndNotify());
window.addEventListener('domnai:signed-out', () => {
  window.__domnaiBillingStatus = null;
});

window.setTimeout(() => {
  refreshBillingStatusAndNotify();
  applyFlowStabilityFixes();
}, 250);
