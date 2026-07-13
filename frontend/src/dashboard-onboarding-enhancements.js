const ONBOARDING_CACHE_PREFIX = 'domnai:onboarding-status:v2:';
const LEGACY_ONBOARDING_CACHE_KEY = 'domnai:onboarding-status:v1';
const ONBOARDING_CACHE_MAX_AGE = 60 * 1000;
const ONBOARDING_REFRESH_AGE = 15 * 1000;

const ONBOARDING_STATES = Object.freeze({
  CHECKING: 'checking',
  PLAN_REQUIRED: 'plan_required',
  PROFILE_REQUIRED: 'profile_required',
  RELEASED: 'released',
});

let currentOnboardingUserId = null;
let lastOnboardingStatus = null;
let lastOnboardingCheckedAt = 0;
let gateRunning = false;
let retryTimer = null;
let revealTimer = null;
let onboardingFrame = 0;
let onboardingState = ONBOARDING_STATES.CHECKING;
let appliedOnboardingState = null;

function onboardingCacheKey(userId) {
  return `${ONBOARDING_CACHE_PREFIX}${userId}`;
}

function clearLegacyOnboardingCache() {
  try {
    sessionStorage.removeItem(LEGACY_ONBOARDING_CACHE_KEY);
  } catch {
    // O fluxo continua sem armazenamento local.
  }
}

function setOnboardingState(nextState) {
  onboardingState = nextState;
  document.documentElement.dataset.onboardingState = nextState;
}

function clearOnboardingState() {
  window.clearTimeout(retryTimer);
  window.clearTimeout(revealTimer);
  retryTimer = null;
  revealTimer = null;
  gateRunning = false;
  currentOnboardingUserId = null;
  lastOnboardingStatus = null;
  lastOnboardingCheckedAt = 0;
  appliedOnboardingState = null;
  setOnboardingState(ONBOARDING_STATES.CHECKING);
  document.documentElement.classList.remove(
    'domnai-gate-pending',
    'domnai-plan-selection-required',
    'domnai-profile-modal-open',
  );
  const shell = document.querySelector('.domnai-app-shell');
  shell?.classList.remove('onboarding-plan-mode');
  shell?.removeAttribute('data-plan-gate');
  shell?.querySelector('.domnai-gate-cancel')?.remove();
}

function readCachedOnboardingStatus(userId) {
  try {
    const cached = JSON.parse(sessionStorage.getItem(onboardingCacheKey(userId)) || 'null');
    if (!cached?.status || Date.now() - Number(cached.savedAt || 0) > ONBOARDING_CACHE_MAX_AGE) return null;
    lastOnboardingCheckedAt = Number(cached.savedAt || 0);
    return cached.status;
  } catch {
    return null;
  }
}

function cacheOnboardingStatus(userId, status) {
  lastOnboardingCheckedAt = Date.now();
  try {
    sessionStorage.setItem(onboardingCacheKey(userId), JSON.stringify({ status, savedAt: lastOnboardingCheckedAt }));
  } catch {
    // Cache é apenas uma otimização.
  }
}

async function waitForAuthenticatedSession() {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    const clerk = window.Clerk;
    if (clerk?.loaded && !clerk.session) return null;
    if (clerk?.session && clerk?.user?.id) return { session: clerk.session, userId: clerk.user.id };
    await new Promise((resolve) => window.setTimeout(resolve, 75));
  }
  return null;
}

async function onboardingStatus(session) {
  const token = await session.getToken();
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch('/api/billing/status', {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
      signal: controller.signal,
    });
    if (!response.ok) throw new Error('Não foi possível validar o plano.');
    return await response.json();
  } finally {
    window.clearTimeout(timeout);
  }
}

function billingButton() {
  return [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Faturamento'));
}

function openBillingSection() {
  if (onboardingState !== ONBOARDING_STATES.PLAN_REQUIRED) return;
  const button = billingButton();
  if (button && !button.classList.contains('is-active')) button.click();
}

function needsPlanSelection(status) {
  return status?.plan === 'unselected' || status?.plan === 'free_demo' || !status?.plan;
}

function hasCompletedAccess(status) {
  return !needsPlanSelection(status) && Boolean(status?.profileCompleted);
}

function stateFromStatus(status) {
  if (onboardingState === ONBOARDING_STATES.PROFILE_REQUIRED && !hasCompletedAccess(status)) {
    return ONBOARDING_STATES.PROFILE_REQUIRED;
  }
  if (needsPlanSelection(status)) return ONBOARDING_STATES.PLAN_REQUIRED;
  if (!status?.profileCompleted) return ONBOARDING_STATES.PROFILE_REQUIRED;
  return ONBOARDING_STATES.RELEASED;
}

function showCancelOverlay() {
  if (document.querySelector('.domnai-cancel-overlay')) return;
  document.body.insertAdjacentHTML('beforeend', `
    <section class="domnai-cancel-overlay" aria-live="polite" aria-busy="true">
      <div>
        <strong>Encerrando acesso...</strong>
        <p>Aguarde um instante.</p>
      </div>
    </section>
  `);
}

async function cancelPlanSelection(button) {
  if (button) {
    button.disabled = true;
    button.textContent = 'Saindo...';
  }

  showCancelOverlay();

  try {
    if (!window.Clerk?.signOut) throw new Error('Sessão não encontrada.');
    try {
      Object.keys(sessionStorage).forEach((key) => {
        if (key.startsWith('domnai:')) sessionStorage.removeItem(key);
      });
    } catch {
      // O encerramento continua mesmo sem acesso ao armazenamento.
    }
    await window.Clerk.signOut();
    window.location.replace(`${window.location.origin}${window.location.pathname}#/`);
    window.setTimeout(() => window.location.reload(), 50);
  } catch (error) {
    document.querySelector('.domnai-cancel-overlay')?.remove();
    if (button) {
      button.disabled = false;
      button.textContent = 'Cancelar';
    }
    window.alert(error?.message || 'Não foi possível cancelar agora.');
  }
}

function installGateCancelButton() {
  const shell = document.querySelector('.domnai-app-shell');
  if (!shell || shell.querySelector('.domnai-gate-cancel')) return;

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'domnai-gate-cancel';
  button.textContent = 'Cancelar';
  button.setAttribute('aria-label', 'Cancelar escolha de plano e sair da conta');
  button.addEventListener('click', () => cancelPlanSelection(button));
  shell.appendChild(button);
}

function revealPlanScreenWhenReady(attempt = 0) {
  window.clearTimeout(revealTimer);
  if (onboardingState !== ONBOARDING_STATES.PLAN_REQUIRED) return;

  const billingHeader = document.querySelector('.billing-page-header');
  const plans = document.querySelector('.billing-plans-section');
  if (billingHeader && plans) {
    document.documentElement.classList.remove('domnai-gate-pending');
    installGateCancelButton();
    return;
  }

  openBillingSection();
  if (attempt < 40) {
    revealTimer = window.setTimeout(() => revealPlanScreenWhenReady(attempt + 1), 100);
  } else {
    showGateRecovery();
  }
}

function showGateRecovery() {
  if (onboardingState !== ONBOARDING_STATES.PLAN_REQUIRED) return;
  document.documentElement.classList.remove('domnai-gate-pending');
  const shell = document.querySelector('.domnai-app-shell');
  if (!shell || shell.querySelector('.domnai-gate-recovery')) return;
  shell.insertAdjacentHTML('beforeend', `
    <section class="domnai-gate-recovery" role="alert">
      <div>
        <strong>Não foi possível abrir a escolha de plano.</strong>
        <p>Verifique sua conexão e tente novamente.</p>
        <button type="button" data-gate-retry>Tentar novamente</button>
        <button type="button" data-gate-logout>Sair da conta</button>
      </div>
    </section>
  `);
  shell.querySelector('[data-gate-retry]')?.addEventListener('click', () => enforcePlanGate(true));
  shell.querySelector('[data-gate-logout]')?.addEventListener('click', () => cancelPlanSelection(shell.querySelector('[data-gate-logout]')));
}

function lockPlatformForPlanSelection() {
  if (onboardingState !== ONBOARDING_STATES.PLAN_REQUIRED) return;
  const shell = document.querySelector('.domnai-app-shell');
  if (!shell) {
    scheduleGateRetry(100, false);
    return;
  }

  shell.querySelector('.domnai-gate-recovery')?.remove();
  shell.classList.add('onboarding-plan-mode');
  shell.setAttribute('data-plan-gate', 'required');
  installGateCancelButton();

  if (appliedOnboardingState !== ONBOARDING_STATES.PLAN_REQUIRED) {
    appliedOnboardingState = ONBOARDING_STATES.PLAN_REQUIRED;
    openBillingSection();
    revealPlanScreenWhenReady();
  }
}

function holdPlatformForProfile() {
  window.clearTimeout(revealTimer);
  document.documentElement.classList.remove('domnai-gate-pending');
  document.documentElement.classList.add('domnai-plan-selection-required', 'domnai-profile-modal-open');
  const shell = document.querySelector('.domnai-app-shell');
  if (!shell) return;
  shell.querySelector('.domnai-gate-recovery')?.remove();
  shell.classList.add('onboarding-plan-mode');
  shell.setAttribute('data-plan-gate', 'profile-required');
  installGateCancelButton();
  appliedOnboardingState = ONBOARDING_STATES.PROFILE_REQUIRED;
}

function releasePlatformAfterPlanSelection() {
  const shell = document.querySelector('.domnai-app-shell');
  window.clearTimeout(revealTimer);
  document.documentElement.classList.remove(
    'domnai-gate-pending',
    'domnai-plan-selection-required',
    'domnai-profile-modal-open',
  );
  appliedOnboardingState = ONBOARDING_STATES.RELEASED;
  if (!shell) return;

  shell.querySelector('.domnai-gate-recovery')?.remove();
  shell.querySelector('.domnai-gate-cancel')?.remove();
  shell.classList.remove('onboarding-plan-mode');
  shell.setAttribute('data-plan-gate', 'released');
  document.querySelectorAll('.domnai-main-area > [aria-hidden="true"]').forEach((node) => node.removeAttribute('aria-hidden'));
}

function applyPlanGate(status) {
  lastOnboardingStatus = status;
  const nextState = stateFromStatus(status);
  setOnboardingState(nextState);

  if (nextState === ONBOARDING_STATES.PLAN_REQUIRED) {
    document.documentElement.classList.add('domnai-plan-selection-required', 'domnai-gate-pending');
    document.documentElement.classList.remove('domnai-profile-modal-open');
    lockPlatformForPlanSelection();
    return;
  }

  if (nextState === ONBOARDING_STATES.PROFILE_REQUIRED) {
    holdPlatformForProfile();
    return;
  }

  if (nextState === ONBOARDING_STATES.RELEASED && hasCompletedAccess(status)) {
    releasePlatformAfterPlanSelection();
  }
}

function scheduleGateRetry(delay = 600, force = false) {
  window.clearTimeout(retryTimer);
  retryTimer = window.setTimeout(() => enforcePlanGate(force), delay);
}

async function enforcePlanGate(force = false) {
  if (gateRunning || onboardingState === ONBOARDING_STATES.PROFILE_REQUIRED) return;
  gateRunning = true;

  try {
    const auth = await waitForAuthenticatedSession();
    if (!auth) {
      clearOnboardingState();
      return;
    }

    const { session, userId } = auth;
    if (currentOnboardingUserId !== userId) {
      currentOnboardingUserId = userId;
      lastOnboardingStatus = null;
      lastOnboardingCheckedAt = 0;
      appliedOnboardingState = null;
      setOnboardingState(ONBOARDING_STATES.CHECKING);
      clearLegacyOnboardingCache();
    }

    if (!force && lastOnboardingStatus && Date.now() - lastOnboardingCheckedAt < ONBOARDING_REFRESH_AGE) {
      applyPlanGate(lastOnboardingStatus);
      return;
    }

    if (!force && !lastOnboardingStatus) {
      const cached = readCachedOnboardingStatus(userId);
      if (cached) {
        lastOnboardingStatus = cached;
        applyPlanGate(cached);
      }
    }

    if (onboardingState === ONBOARDING_STATES.CHECKING) {
      document.documentElement.classList.add('domnai-gate-pending');
    }
    const status = await onboardingStatus(session);
    cacheOnboardingStatus(userId, status);
    applyPlanGate(status);
    window.__domnaiBillingStatus = status;
  } catch (error) {
    console.error('[DomnAI] Falha ao validar plano:', error);
    if (lastOnboardingStatus) {
      applyPlanGate(lastOnboardingStatus);
    } else {
      setOnboardingState(ONBOARDING_STATES.PLAN_REQUIRED);
      document.documentElement.classList.add('domnai-plan-selection-required');
      lockPlatformForPlanSelection();
      showGateRecovery();
    }
  } finally {
    gateRunning = false;
  }
}

function splitBirthDate(value) {
  const [year = '', month = '', day = ''] = String(value || '').split('-');
  return { day, month, year };
}

function syncBirthDate(wrapper) {
  const day = wrapper.querySelector('[name="birthDay"]')?.value.padStart(2, '0') || '';
  const month = wrapper.querySelector('[name="birthMonth"]')?.value.padStart(2, '0') || '';
  const year = wrapper.querySelector('[name="birthYear"]')?.value || '';
  const hidden = wrapper.querySelector('[name="birthDate"]');
  if (hidden) hidden.value = day && month && year.length === 4 ? `${year}-${month}-${day}` : '';
}

function enhanceBirthDate(root = document) {
  root.querySelectorAll?.('.profile-checklist-form input[name="birthDate"]:not([data-split-ready])').forEach((input) => {
    input.dataset.splitReady = 'true';
    const { day, month, year } = splitBirthDate(input.value);
    const label = input.closest('label');
    if (!label) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'birth-date-split';
    wrapper.innerHTML = `
      <input type="hidden" name="birthDate" value="${input.value || ''}">
      <label>Dia<input name="birthDay" inputmode="numeric" maxlength="2" placeholder="DD" value="${day}" required></label>
      <label>Mês<input name="birthMonth" inputmode="numeric" maxlength="2" placeholder="MM" value="${month}" required></label>
      <label>Ano<input name="birthYear" inputmode="numeric" maxlength="4" placeholder="AAAA" value="${year}" required></label>
    `;

    label.replaceWith(wrapper);
    wrapper.querySelectorAll('input:not([type="hidden"])').forEach((field) => {
      field.addEventListener('input', () => {
        field.value = field.value.replace(/\D/g, '').slice(0, Number(field.maxLength));
        syncBirthDate(wrapper);
      });
    });
    syncBirthDate(wrapper);
  });
}

const onboardingObserver = new MutationObserver((mutations) => {
  if (onboardingFrame) return;
  onboardingFrame = window.requestAnimationFrame(() => {
    onboardingFrame = 0;
    const addedRoot = mutations.flatMap((mutation) => [...mutation.addedNodes])
      .find((node) => node.nodeType === Node.ELEMENT_NODE) || document;
    enhanceBirthDate(addedRoot);
  });
});

onboardingObserver.observe(document.body || document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => {
  if (onboardingState === ONBOARDING_STATES.PLAN_REQUIRED) window.requestAnimationFrame(openBillingSection);
});
window.addEventListener('pageshow', () => enforcePlanGate(true));
document.addEventListener('visibilitychange', () => {
  if (
    document.visibilityState === 'visible'
    && onboardingState !== ONBOARDING_STATES.PROFILE_REQUIRED
    && Date.now() - lastOnboardingCheckedAt > ONBOARDING_REFRESH_AGE
  ) enforcePlanGate(true);
});
window.addEventListener('domnai:onboarding-profile-opened', () => {
  setOnboardingState(ONBOARDING_STATES.PROFILE_REQUIRED);
  holdPlatformForProfile();
});
window.addEventListener('domnai:onboarding-profile-cancelled', () => {
  setOnboardingState(ONBOARDING_STATES.PLAN_REQUIRED);
  appliedOnboardingState = null;
  applyPlanGate(lastOnboardingStatus || { plan: 'unselected', profileCompleted: false });
});
window.addEventListener('domnai:billing-updated', (event) => {
  const status = event.detail;
  if (status && currentOnboardingUserId) {
    cacheOnboardingStatus(currentOnboardingUserId, status);
    applyPlanGate(status);
  } else {
    setOnboardingState(ONBOARDING_STATES.CHECKING);
    enforcePlanGate(true);
  }
});
window.addEventListener('domnai:signed-out', clearOnboardingState);

clearLegacyOnboardingCache();
setOnboardingState(ONBOARDING_STATES.CHECKING);
enhanceBirthDate();
window.setTimeout(() => enforcePlanGate(true), 100);
