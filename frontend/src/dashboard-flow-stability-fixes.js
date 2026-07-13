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

function stabilizeBillingBackButton() {
  document.querySelectorAll('[data-billing-action="back-to-chat"]:not([data-flow-fixed])').forEach((button) => {
    button.dataset.flowFixed = 'true';
    button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (!planIsSelected()) return;
      openDashboardSafely();
    }, true);

    if (!planIsSelected()) {
      button.hidden = true;
      button.setAttribute('aria-hidden', 'true');
    }
  });
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

function watchPlanSelection() {
  document.querySelectorAll('[data-billing-action="free"]:not([data-status-watch])').forEach((button) => {
    button.dataset.statusWatch = 'true';
    button.addEventListener('click', () => {
      let attempts = 0;
      const poll = async () => {
        attempts += 1;
        const status = await refreshBillingStatusAndNotify();
        if (planIsSelected(status) || attempts >= 8) return;
        window.setTimeout(poll, 500);
      };
      window.setTimeout(poll, 350);
    });
  });
}

function applyFlowStabilityFixes() {
  stabilizeBillingBackButton();
  stabilizeProfileBackButton();
  enhanceBillingFailureState();
  watchPlanSelection();
}

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
