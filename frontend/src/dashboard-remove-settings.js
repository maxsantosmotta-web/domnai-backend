function removeInactiveSettingsModule() {
  const settingsButton = [...document.querySelectorAll('.sidebar-system-group button')]
    .find((button) => button.textContent.trim().includes('Configurações'));

  if (settingsButton) settingsButton.remove();

  const settingsSection = [...document.querySelectorAll('.domnai-main-area > .internal-section')]
    .find((section) => section.querySelector('h1')?.textContent.trim() === 'Preferências da plataforma');

  if (settingsSection) {
    const wasVisible = settingsSection.offsetParent !== null;
    settingsSection.remove();

    if (wasVisible) {
      const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
        .find((button) => button.textContent.trim().includes('Dashboard'));
      dashboardButton?.click();
    }
  }
}

const removeSettingsObserver = new MutationObserver(removeInactiveSettingsModule);
removeSettingsObserver.observe(document.documentElement, { childList: true, subtree: true });
removeInactiveSettingsModule();
