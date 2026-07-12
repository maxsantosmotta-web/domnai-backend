function cleanSidebarNavigation() {
  const sidebar = document.querySelector('.domnai-sidebar');
  if (!sidebar) return;

  const dashboardButton = [...sidebar.querySelectorAll('button')]
    .find((button) => String(button.textContent || '').trim() === 'Dashboard');

  if (dashboardButton) {
    dashboardButton.classList.add('domnai-dashboard-item-hidden');
    dashboardButton.setAttribute('aria-hidden', 'true');
    dashboardButton.setAttribute('tabindex', '-1');
    dashboardButton.disabled = true;
  }

  const operationsLabel = [...sidebar.querySelectorAll('*')]
    .find((element) => element.children.length === 0 && String(element.textContent || '').trim().toUpperCase() === 'OPERAÇÕES');

  if (operationsLabel) {
    operationsLabel.classList.add('domnai-operations-label');
    operationsLabel.setAttribute('aria-label', 'Operações disponíveis');
  }
}

const sidebarCleanupObserver = new MutationObserver(() => {
  window.requestAnimationFrame(cleanSidebarNavigation);
});

sidebarCleanupObserver.observe(document.documentElement, { childList: true, subtree: true });
cleanSidebarNavigation();
