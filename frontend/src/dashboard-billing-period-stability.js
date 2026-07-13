let selectedBillingPeriod = 'monthly';
let lastBillingCard = null;
let profileModalOpen = false;

function applySelectedBillingPeriod() {
  const premiumCard = document.querySelector('.billing-premium-card');
  if (!premiumCard) {
    lastBillingCard = null;
    return;
  }

  const switcher = premiumCard.querySelector('.billing-period-switch');
  const monthlyButton = switcher?.querySelector('[data-billing-period="monthly"]');
  const yearlyButton = switcher?.querySelector('[data-billing-period="yearly"]');
  const price = premiumCard.querySelector(':scope > strong');
  const copy = premiumCard.querySelector('.billing-period-copy');
  const checkout = premiumCard.querySelector('[data-billing-product]');

  if (!switcher || !monthlyButton || !yearlyButton || !price || !copy || !checkout) return;

  const annual = selectedBillingPeriod === 'yearly';

  monthlyButton.classList.toggle('is-active', !annual);
  yearlyButton.classList.toggle('is-active', annual);
  yearlyButton.innerHTML = annual ? 'Anual<span>Economize 17%</span>' : 'Anual';
  price.innerHTML = annual
    ? 'R$ 599,00 <small>/ano</small>'
    : 'R$ 59,90 <small>/mês</small>';
  copy.textContent = annual
    ? 'Cobrança anual com 500 créditos renovados mensalmente.'
    : 'Cobrança mensal com 500 créditos por ciclo.';
  checkout.dataset.billingProduct = annual ? 'premium_yearly' : 'premium_monthly';
  premiumCard.dataset.selectedPeriod = selectedBillingPeriod;
  lastBillingCard = premiumCard;
}

function syncProfileModalState() {
  const overlay = document.querySelector('.profile-checklist-overlay');
  const isOpen = Boolean(overlay);

  if (isOpen) {
    profileModalOpen = true;
    document.documentElement.classList.remove('domnai-gate-pending');
    document.documentElement.classList.add('domnai-profile-modal-open');
    return;
  }

  if (profileModalOpen) {
    profileModalOpen = false;
    document.documentElement.classList.remove('domnai-profile-modal-open');
  }
}

// Impede o gate de reabrir a seção de faturamento enquanto o cadastro obrigatório está aberto.
document.addEventListener('click', (event) => {
  if (!document.querySelector('.profile-checklist-overlay')) return;

  const navigationButton = event.target.closest?.('.sidebar-navigation button');
  if (!navigationButton) return;
  if (!navigationButton.textContent.trim().includes('Faturamento')) return;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
}, true);

// Captura somente o seletor Mensal/Anual.
document.addEventListener('click', (event) => {
  const button = event.target.closest?.('[data-billing-period]');
  if (!button) return;

  const period = button.dataset.billingPeriod;
  if (!['monthly', 'yearly'].includes(period)) return;

  selectedBillingPeriod = period;
  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  applySelectedBillingPeriod();
}, true);

const billingPeriodObserver = new MutationObserver(() => {
  syncProfileModalState();

  const currentCard = document.querySelector('.billing-premium-card');
  if (!currentCard || currentCard === lastBillingCard) return;
  window.requestAnimationFrame(applySelectedBillingPeriod);
});

billingPeriodObserver.observe(document.documentElement, {
  childList: true,
  subtree: true,
});

syncProfileModalState();
window.requestAnimationFrame(applySelectedBillingPeriod);
