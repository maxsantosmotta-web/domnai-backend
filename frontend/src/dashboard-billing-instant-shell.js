function billingReturnImmediately(event) {
  event?.preventDefault();
  event?.stopPropagation();
  event?.stopImmediatePropagation?.();

  const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Dashboard'));

  if (dashboardButton) {
    dashboardButton.click();
    return;
  }

  window.location.hash = '#/';
}

function bindImmediateBillingBack(section) {
  const button = section.querySelector('.billing-back-to-chat, .module-back-button');
  if (!button || button.dataset.instantBillingBack === 'true') return;

  button.dataset.instantBillingBack = 'true';
  button.textContent = 'Voltar';
  button.classList.add('module-back-button');
  button.addEventListener('click', billingReturnImmediately, true);
}

function renderBillingShell(section) {
  const loading = section.querySelector('.billing-loading-state');
  if (!loading || section.dataset.instantShell === 'true') return;

  section.dataset.instantShell = 'true';
  section.innerHTML = `
    <header class="billing-page-header billing-instant-header">
      <div>
        <span>Faturamento</span>
        <h1>Plano e créditos</h1>
        <p>Acompanhe seu saldo, assinatura e pacotes adicionais.</p>
      </div>
      <button type="button" class="billing-back-to-chat module-back-button" aria-label="Voltar ao chat">Voltar</button>
    </header>
    <div class="billing-instant-content" aria-hidden="true">
      <div class="billing-instant-card"></div>
      <div class="billing-instant-card"></div>
      <div class="billing-instant-card"></div>
    </div>
  `;
  bindImmediateBillingBack(section);
}

function enhanceBillingResponsiveness() {
  document.querySelectorAll('.internal-section').forEach((section) => {
    const label = section.querySelector(':scope > header span')?.textContent.trim();
    const isBilling = label === 'Faturamento' || section.querySelector('.billing-loading-state, .billing-page-header');
    if (!isBilling) return;

    renderBillingShell(section);
    bindImmediateBillingBack(section);
  });
}

const instantBillingObserver = new MutationObserver(() => {
  window.requestAnimationFrame(enhanceBillingResponsiveness);
});
instantBillingObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.setTimeout(enhanceBillingResponsiveness, 0));
enhanceBillingResponsiveness();
