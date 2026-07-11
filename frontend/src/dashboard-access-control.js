let domnaiAccessStatus = null;
let domnaiAccessBusy = false;
let domnaiAccessTimer = null;

async function domnaiAccessToken() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session.getToken();
    await new Promise((resolve) => window.setTimeout(resolve, 120));
  }
  return '';
}

async function refreshDomnAIAccess() {
  if (domnaiAccessBusy) return;
  domnaiAccessBusy = true;
  try {
    const token = await domnaiAccessToken();
    if (!token) return;
    const response = await fetch('/api/billing/status', {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!response.ok) return;
    domnaiAccessStatus = await response.json();
    const html = document.documentElement;
    html.classList.toggle('domnai-access-premium', Boolean(domnaiAccessStatus.premiumActive));
    html.classList.toggle('domnai-access-free', domnaiAccessStatus.plan === 'free' && !domnaiAccessStatus.premiumActive);
    html.classList.toggle('domnai-access-unselected', !domnaiAccessStatus.plan || domnaiAccessStatus.plan === 'unselected');
  } finally {
    domnaiAccessBusy = false;
  }
}

function openPremiumNotice() {
  document.querySelector('.domnai-premium-notice')?.remove();
  document.body.insertAdjacentHTML('beforeend', `
    <div class="domnai-premium-notice" role="dialog" aria-modal="true">
      <section>
        <span>Recurso PREMIUM</span>
        <h2>Este recurso não está disponível no plano FREE</h2>
        <p>Assine o PREMIUM para utilizar operações, chat, arquivos, Biblioteca e Lixeira.</p>
        <div>
          <button type="button" class="domnai-premium-notice-close">Continuar no FREE</button>
          <button type="button" class="domnai-premium-notice-upgrade">Ver plano PREMIUM</button>
        </div>
      </section>
    </div>
  `);
  const notice = document.querySelector('.domnai-premium-notice');
  notice.querySelector('.domnai-premium-notice-close')?.addEventListener('click', () => notice.remove());
  notice.querySelector('.domnai-premium-notice-upgrade')?.addEventListener('click', () => {
    notice.remove();
    const billingButton = [...document.querySelectorAll('.sidebar-navigation button')]
      .find((button) => button.textContent.trim().includes('Faturamento'));
    billingButton?.click();
  });
}

function isFreeRestrictedTarget(target) {
  if (!target) return false;
  const text = target.textContent?.trim() || '';
  const operationButton = target.closest('.operations-only button');
  const systemButton = target.closest('.sidebar-system-group button');
  const restrictedSystem = systemButton && (text.includes('Biblioteca') || text.includes('Lixeira'));
  const composer = target.closest('.chat-composer, .composer-plus-menu');
  return Boolean(operationButton || restrictedSystem || composer || target.closest('.conversation-options-menu'));
}

function blockFreeInteraction(event) {
  if (!document.documentElement.classList.contains('domnai-access-free')) return;
  if (!isFreeRestrictedTarget(event.target)) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  openPremiumNotice();
}

document.addEventListener('click', blockFreeInteraction, true);
document.addEventListener('submit', blockFreeInteraction, true);

function keepProfileReachable() {
  const sidebar = document.querySelector('.domnai-sidebar');
  const profile = document.querySelector('.sidebar-profile');
  if (!sidebar || !profile) return;
  profile.classList.add('domnai-profile-visible');
}

const domnaiAccessObserver = new MutationObserver(() => {
  keepProfileReachable();
  window.clearTimeout(domnaiAccessTimer);
  domnaiAccessTimer = window.setTimeout(refreshDomnAIAccess, 100);
});

domnaiAccessObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('focus', refreshDomnAIAccess);
window.addEventListener('pageshow', refreshDomnAIAccess);
window.addEventListener('hashchange', refreshDomnAIAccess);
window.setInterval(refreshDomnAIAccess, 2500);
keepProfileReachable();
refreshDomnAIAccess();
