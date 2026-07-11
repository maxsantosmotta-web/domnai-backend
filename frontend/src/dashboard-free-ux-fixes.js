function openNativeProfileFromSidebar(event) {
  const trigger = event.target.closest('.domnai-profile-trigger, .sidebar-profile');
  if (!trigger) return;

  event.preventDefault();
  event.stopPropagation();

  if (typeof window.openDomnAIProfile === 'function') {
    window.openDomnAIProfile();
    return;
  }

  const profileButton = trigger.querySelector('.domnai-profile-trigger');
  profileButton?.click();
}

document.addEventListener('click', openNativeProfileFromSidebar, true);

function refineFreePlanMessages() {
  document.querySelectorAll('body *').forEach((element) => {
    if (element.children.length) return;
    const text = element.textContent.trim();

    if (text === 'Chat disponível no plano PREMIUM') {
      element.remove();
      return;
    }

    if (text === 'Este recurso não está disponível no plano FREE') {
      element.textContent = 'Recurso disponível no PREMIUM';
      return;
    }

    if (text === 'Assine o PREMIUM para utilizar operações, chat, arquivos, Biblioteca e Lixeira.') {
      element.textContent = 'Este recurso faz parte do plano PREMIUM. Você pode continuar navegando no FREE ou conhecer o acesso completo.';
    }
  });

  const planLogout = document.querySelector('.domnai-plan-logout');
  if (planLogout) planLogout.remove();
}

const freeUxObserver = new MutationObserver(refineFreePlanMessages);
freeUxObserver.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
refineFreePlanMessages();
