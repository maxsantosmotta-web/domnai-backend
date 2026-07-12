function hideInactiveSettingsModule() {
  const settingsButton = [...document.querySelectorAll('.sidebar-system-group button')]
    .find((button) => button.textContent.trim().includes('Configurações'));

  if (settingsButton) {
    settingsButton.classList.add('domnai-settings-hidden');
    settingsButton.setAttribute('aria-hidden', 'true');
    settingsButton.setAttribute('tabindex', '-1');
  }

  const settingsSection = [...document.querySelectorAll('.domnai-main-area > .internal-section')]
    .find((section) => section.querySelector('h1')?.textContent.trim() === 'Preferências da plataforma');

  if (settingsSection) {
    settingsSection.classList.add('domnai-settings-hidden');
    settingsSection.setAttribute('aria-hidden', 'true');
  }
}

const hideSettingsObserver = new MutationObserver(hideInactiveSettingsModule);
hideSettingsObserver.observe(document.documentElement, { childList: true, subtree: true });
hideInactiveSettingsModule();
