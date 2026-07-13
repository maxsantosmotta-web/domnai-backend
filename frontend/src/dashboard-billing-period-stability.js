function updateBillingPeriod(button) {
  const period = button?.dataset?.billingPeriod;
  if (!['monthly', 'yearly'].includes(period)) return;

  const premiumCard = button.closest('.billing-premium-card');
  if (!premiumCard) return;

  const switcher = premiumCard.querySelector('.billing-period-switch');
  const monthlyButton = switcher?.querySelector('[data-billing-period="monthly"]');
  const yearlyButton = switcher?.querySelector('[data-billing-period="yearly"]');
  const price = premiumCard.querySelector(':scope > strong');
  const copy = premiumCard.querySelector('.billing-period-copy');
  const checkout = premiumCard.querySelector('[data-billing-product]');

  if (!switcher || !monthlyButton || !yearlyButton || !price || !copy || !checkout) return;

  const annual = period === 'yearly';

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
  premiumCard.dataset.selectedPeriod = period;
}

// Captura o toque antes do listener antigo, impedindo que todo o faturamento seja recriado.
document.addEventListener('click', (event) => {
  const button = event.target.closest?.('[data-billing-period]');
  if (!button) return;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  updateBillingPeriod(button);
}, true);
