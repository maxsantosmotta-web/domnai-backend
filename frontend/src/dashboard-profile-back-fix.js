let domnaiProfileClosing = false;

function safelyReturnFromProfile(event) {
  const button = event.target.closest('.domnai-profile-close, .domnai-profile-cancel');
  if (!button || domnaiProfileClosing) return;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();
  domnaiProfileClosing = true;

  const page = document.querySelector('[data-domnai-profile-page]');
  const mainArea = document.querySelector('.domnai-main-area');
  const isDashboardButton = button.classList.contains('domnai-profile-close');
  const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((item) => item.textContent.trim().includes('Dashboard'));

  document.body.classList.remove('domnai-profile-exclusive', 'domnai-mobile-menu-open');
  mainArea?.classList.remove('profile-page-open');

  if (page?.parentNode && page.parentNode.contains(page)) {
    page.parentNode.removeChild(page);
  }

  window.requestAnimationFrame(() => {
    try {
      if (isDashboardButton) {
        const mobileMenuButton = document.querySelector('.mobile-menu-button');
        if (window.matchMedia('(max-width: 820px)').matches) {
          window.setTimeout(() => mobileMenuButton?.click(), 40);
        }
      } else {
        dashboardButton?.click();
      }
    } finally {
      window.setTimeout(() => {
        domnaiProfileClosing = false;
      }, 150);
    }
  });
}

document.addEventListener('click', safelyReturnFromProfile, true);