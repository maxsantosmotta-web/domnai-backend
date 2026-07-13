let selectedBillingPeriod = 'monthly';
let billingPeriodApplyQueued = false;

function applySelectedBillingPeriod() {
  billingPeriodApplyQueued = false;

  const premiumCard = document.querySelector('.billing-premium-card');
  if (!premiumCard) return;

  const switcher = premiumCard.querySelector('.billing-period-switch');
  const monthlyButton = switcher?.querySelector('[data-billing-period="monthly"]');
  const yearlyButton = switcher?.querySelector('[data-billing-period="yearly"]');
  const price = premiumCard.querySelector(':scope > strong');
  const copy = premiumCard.querySelector('.billing-period-copy');
  const checkout = premiumCard.querySelector('[data-billing-product]');

  if (!switcher || !monthlyButton || !yearlyButton || !price || !copy || !checkout) return;

  const annual = selectedBillingPeriod === 'yearly';
  const expectedYearlyHtml = annual ? 'Anual<span>Economize 17%</span>' : 'Anual';
  const expectedPriceHtml = annual
    ? 'R$ 599,00 <small>/ano</small>'
    : 'R$ 59,90 <small>/mês</small>';
  const expectedCopy = annual
    ? 'Cobrança anual com 500 créditos renovados mensalmente.'
    : 'Cobrança mensal com 500 créditos por ciclo.';
  const expectedProduct = annual ? 'premium_yearly' : 'premium_monthly';

  monthlyButton.classList.toggle('is-active', !annual);
  yearlyButton.classList.toggle('is-active', annual);

  if (yearlyButton.innerHTML !== expectedYearlyHtml) yearlyButton.innerHTML = expectedYearlyHtml;
  if (price.innerHTML !== expectedPriceHtml) price.innerHTML = expectedPriceHtml;
  if (copy.textContent !== expectedCopy) copy.textContent = expectedCopy;
  if (checkout.dataset.billingProduct !== expectedProduct) checkout.dataset.billingProduct = expectedProduct;

  premiumCard.dataset.selectedPeriod = selectedBillingPeriod;
}

function queueBillingPeriodApply() {
  if (billingPeriodApplyQueued) return;
  billingPeriodApplyQueued = true;
  window.requestAnimationFrame(applySelectedBillingPeriod);
}

// Assume o clique antes da lógica antiga e mantém a escolha mesmo se a tela for reconstruída ao fundo.
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
  if (!document.querySelector('.billing-premium-card')) return;
  queueBillingPeriodApply();
});

billingPeriodObserver.observe(document.documentElement, { childList: true, subtree: true });
queueBillingPeriodApply();
