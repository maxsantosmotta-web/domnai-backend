function translateValidationMessage(text) {
  return String(text || '')
    .replace(/String should have at least (\d+) characters?/gi, 'deve ter pelo menos $1 caracteres')
    .replace(/String should have at most (\d+) characters?/gi, 'deve ter no máximo $1 caracteres')
    .replace(/Field required/gi, 'campo obrigatório')
    .replace(/Input should be a valid date/gi, 'informe uma data válida')
    .replace(/Input should be a valid string/gi, 'informe um texto válido')
    .replace(/Value error/gi, 'valor inválido')
    .replace(/Input should be greater than/gi, 'o valor deve ser maior que')
    .replace(/Input should be less than/gi, 'o valor deve ser menor que');
}

function localizeProfileErrors() {
  document.querySelectorAll('.profile-checklist-error').forEach((element) => {
    const translated = translateValidationMessage(element.textContent);
    if (translated !== element.textContent) element.textContent = translated;
  });
}

const profileErrorObserver = new MutationObserver(localizeProfileErrors);
profileErrorObserver.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
localizeProfileErrors();
