function normalizeInternalBackButton() {
  const embeddedBillingButton = document.querySelector('.billing-back-to-chat');
  if (embeddedBillingButton) embeddedBillingButton.hidden = true;

  const globalButton = document.querySelector('.global-exit-button');
  if (!globalButton) return;

  globalButton.textContent = 'Voltar';
  globalButton.setAttribute('aria-label', 'Voltar ao chat');
}

const observer = new MutationObserver(() => window.requestAnimationFrame(normalizeInternalBackButton));
observer.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.setTimeout(normalizeInternalBackButton, 50));
normalizeInternalBackButton();
