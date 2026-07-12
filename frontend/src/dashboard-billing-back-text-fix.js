function normalizeBillingBackButton() {
  const button = document.querySelector('.billing-back-to-chat');
  if (!button || button.dataset.labelFixed === 'true') return;
  button.dataset.labelFixed = 'true';
  button.textContent = 'Voltar';
  button.setAttribute('aria-label', 'Voltar ao chat');
}

const observer = new MutationObserver(() => window.requestAnimationFrame(normalizeBillingBackButton));
observer.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.setTimeout(normalizeBillingBackButton, 50));
normalizeBillingBackButton();
