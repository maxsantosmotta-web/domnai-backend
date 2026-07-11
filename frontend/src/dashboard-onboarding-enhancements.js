document.documentElement.classList.add('domnai-gate-pending');

let lastOnboardingStatus = null;
let gateRunning = false;
let retryTimer = null;

async function onboardingToken() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session.getToken();
    await new Promise((resolve) => window.setTimeout(resolve, 120));
  }
  throw new Error('Sessão não encontrada.');
}

async function onboardingStatus() {
  const token = await onboardingToken();
  const response = await fetch('/api/billing/status', {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Não foi possível validar o plano.');
  return response.json();
}

function openBillingSection() {
  const billingButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Faturamento'));
  if (billingButton && !billingButton.classList.contains('is-active')) billingButton.click();
}

function needsPlanSelection(status) {
  return status?.plan === 'unselected' || status?.plan === 'free_demo' || !status?.plan;
}

function applyPlanGate(status) {
  lastOnboardingStatus = status;
  const needsPlan = needsPlanSelection(status);
  const shell = document.querySelector('.domnai-app-shell');

  document.documentElement.classList.remove('domnai-gate-pending');
  document.documentElement.classList.toggle('domnai-plan-selection-required', needsPlan);

  if (!shell) return;

  shell.classList.toggle('onboarding-plan-mode', needsPlan);
  shell.setAttribute('data-plan-gate', needsPlan ? 'required' : 'released');

  if (needsPlan) {
    openBillingSection();
    window.requestAnimationFrame(openBillingSection);
    window.setTimeout(openBillingSection, 150);
  }
}

function scheduleGateRetry(delay = 500) {
  window.clearTimeout(retryTimer);
  retryTimer = window.setTimeout(enforcePlanGate, delay);
}

async function enforcePlanGate() {
  if (gateRunning) return;
  gateRunning = true;
  try {
    const status = await onboardingStatus();
    applyPlanGate(status);
  } catch {
    document.documentElement.classList.add('domnai-gate-pending');
    scheduleGateRetry(700);
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
  hidden.value = day && month && year.length === 4 ? `${year}-${month}-${day}` : '';
}

function enhanceBirthDate() {
  document.querySelectorAll('.profile-checklist-form input[name="birthDate"]:not([data-split-ready])').forEach((input) => {
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

const onboardingObserver = new MutationObserver(() => {
  enhanceBirthDate();
  if (lastOnboardingStatus) applyPlanGate(lastOnboardingStatus);
  else scheduleGateRetry(100);
});

onboardingObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => scheduleGateRetry(80));
window.addEventListener('focus', () => scheduleGateRetry(80));
window.addEventListener('pageshow', () => scheduleGateRetry(80));

window.setInterval(enforcePlanGate, 1500);

enhanceBirthDate();
enforcePlanGate();
