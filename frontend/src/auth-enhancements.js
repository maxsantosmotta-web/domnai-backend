const EYE_OPEN = `
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
    <circle cx="12" cy="12" r="2.5" />
  </svg>
`;

const EYE_CLOSED = `
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M3 3l18 18" />
    <path d="M10.6 6.2A10.7 10.7 0 0 1 12 6c6 0 9.5 6 9.5 6a17.8 17.8 0 0 1-2.1 2.9" />
    <path d="M6.2 6.2C3.8 8 2.5 12 2.5 12s3.5 6 9.5 6a10.3 10.3 0 0 0 3.2-.5" />
    <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
  </svg>
`;

function normalizeTitle(card) {
  const title = card.querySelector('.custom-auth-header h1');
  if (!title) return;

  if (title.textContent.trim() === 'Criar sua conta') {
    title.textContent = 'Criar conta';
  }

  if (title.textContent.trim() === 'Entrar no DomnAI') {
    title.textContent = 'Entrar';
  }
}

function addPasswordToggle(input) {
  if (input.dataset.visibilityReady === 'true') return;

  const label = input.closest('label');
  if (!label) return;

  input.dataset.visibilityReady = 'true';
  label.classList.add('password-field-label');

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'password-visibility-toggle';
  button.setAttribute('aria-label', 'Mostrar senha');
  button.innerHTML = EYE_OPEN;

  button.addEventListener('click', () => {
    const shouldShow = input.type === 'password';
    input.type = shouldShow ? 'text' : 'password';
    button.setAttribute('aria-label', shouldShow ? 'Ocultar senha' : 'Mostrar senha');
    button.innerHTML = shouldShow ? EYE_CLOSED : EYE_OPEN;
  });

  label.appendChild(button);
}

function enhanceAuthModal() {
  const card = document.querySelector('.custom-auth-card');
  if (!card) return;

  normalizeTitle(card);
  card.querySelectorAll('input[type="password"]').forEach(addPasswordToggle);
}

const observer = new MutationObserver(enhanceAuthModal);
observer.observe(document.documentElement, { childList: true, subtree: true });

enhanceAuthModal();

window.addEventListener('popstate', () => {
  const closeButton = document.querySelector('.custom-auth-close');
  if (!closeButton) return;

  closeButton.click();
  const landingUrl = `${window.location.origin}${window.location.pathname}#/`;
  window.history.pushState({ domnLanding: true }, '', landingUrl);
});
