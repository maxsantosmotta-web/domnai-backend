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

const ALREADY_SIGNED_IN_PATTERN = /you(?:'re| are) already signed in|already signed in|session (?:is )?already active/i;
let recoveringExistingSession = false;

const AUTH_ERROR_TRANSLATIONS = [
  {
    pattern: ALREADY_SIGNED_IN_PATTERN,
    message: 'Sua conta já está conectada. Abrindo o Painel Usuário...',
  },
  {
    pattern: /could(?:n't| not) find (?:your )?account|account (?:was )?not found|identifier.*not found|no account found/i,
    message: 'Não encontramos uma conta com esses dados.',
  },
  {
    pattern: /password is incorrect|incorrect password|wrong password|invalid credentials|credentials.*invalid/i,
    message: 'E-mail ou senha inválidos.',
  },
  {
    pattern: /email address.*(?:taken|already exists|already in use)|identifier.*already exists|account.*already exists|already registered/i,
    message: 'Já existe uma conta cadastrada com este e-mail.',
  },
  {
    pattern: /invalid email|email address is invalid|email.*not valid|identifier is invalid/i,
    message: 'Informe um endereço de e-mail válido.',
  },
  {
    pattern: /password.*(?:data breach|compromised|pwned)/i,
    message: 'Esta senha foi identificada como insegura. Crie uma senha diferente.',
  },
  {
    pattern: /password.*(?:not strong enough|too weak)|weak password/i,
    message: 'A senha não atende aos requisitos de segurança. Use uma senha mais forte.',
  },
  {
    pattern: /password.*(?:at least|minimum|must be).*(?:character|length)|password.*too short/i,
    message: 'A senha não possui o tamanho mínimo exigido.',
  },
  {
    pattern: /verification code.*incorrect|incorrect verification code|code is incorrect|invalid code|code.*not valid/i,
    message: 'O código de verificação está incorreto.',
  },
  {
    pattern: /verification code.*expired|code has expired|expired code/i,
    message: 'O código de verificação expirou. Solicite um novo código.',
  },
  {
    pattern: /too many (?:attempts|requests)|rate limit|try again later/i,
    message: 'Muitas tentativas. Aguarde um momento e tente novamente.',
  },
  {
    pattern: /captcha.*(?:failed|invalid|not verified)|failed.*captcha/i,
    message: 'Não foi possível validar a segurança. Atualize a página e tente novamente.',
  },
  {
    pattern: /session.*(?:expired|not found|does not exist|invalid)|expired session/i,
    message: 'Sua sessão expirou. Faça login novamente.',
  },
  {
    pattern: /account.*(?:locked|blocked|suspended)|user.*(?:locked|blocked|suspended)/i,
    message: 'Esta conta está temporariamente bloqueada. Tente novamente mais tarde.',
  },
  {
    pattern: /access denied|oauth.*(?:cancelled|canceled|denied)|user.*denied/i,
    message: 'O acesso com o Google foi cancelado.',
  },
  {
    pattern: /sign-?up.*(?:disabled|restricted|not allowed)|registration.*(?:disabled|restricted)/i,
    message: 'A criação de novas contas não está disponível no momento.',
  },
  {
    pattern: /email.*not verified|verify your email|verification.*required/i,
    message: 'Confirme seu e-mail para continuar.',
  },
  {
    pattern: /unsupported strategy|strategy.*not supported|method.*not supported/i,
    message: 'Este método de acesso não está disponível no momento.',
  },
  {
    pattern: /failed to fetch|network.*(?:failed|error)|load failed|connection.*failed/i,
    message: 'Não foi possível conectar. Verifique sua internet e tente novamente.',
  },
  {
    pattern: /something went wrong|unexpected error|internal error|unknown error/i,
    message: 'Não foi possível concluir a autenticação. Tente novamente.',
  },
];

const ENGLISH_AUTH_ERROR_MARKERS = /\b(couldn['’]?t|cannot|can['’]?t|your account|password|incorrect|invalid|failed|verification|expired|attempts|try again|not found|already exists|already signed in|not allowed|required|something went wrong)\b/i;

function translateAuthErrorMessage(value) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';

  const translation = AUTH_ERROR_TRANSLATIONS.find(({ pattern }) => pattern.test(text));
  if (translation) return translation.message;

  if (ENGLISH_AUTH_ERROR_MARKERS.test(text)) {
    return 'Não foi possível concluir a autenticação. Confira os dados e tente novamente.';
  }

  return text;
}

function normalizeAuthError(card) {
  card.querySelectorAll('.custom-auth-error').forEach((element) => {
    const current = String(element.textContent || '').trim();
    const translated = translateAuthErrorMessage(current);
    if (translated && translated !== current) element.textContent = translated;
  });
}

function activeClerkSessionExists() {
  const session = window.Clerk?.session;
  return Boolean(session && (!session.status || session.status === 'active'));
}

function recoverExistingSession(card) {
  if (recoveringExistingSession) return true;

  const currentError = String(card.querySelector('.custom-auth-error')?.textContent || '').trim();
  if (!activeClerkSessionExists() && !ALREADY_SIGNED_IN_PATTERN.test(currentError)) return false;

  recoveringExistingSession = true;
  const closeButton = card.querySelector('.custom-auth-close');
  closeButton?.click();

  const userPanelUrl = `${window.location.origin}${window.location.pathname}#/`;
  window.setTimeout(() => window.location.replace(userPanelUrl), 40);
  return true;
}

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

  if (recoverExistingSession(card)) return;
  normalizeTitle(card);
  normalizeAuthError(card);
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
