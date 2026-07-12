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
  const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((item) => item.textContent.trim().includes('Dashboard'));

  document.body.classList.remove('domnai-profile-exclusive', 'domnai-mobile-menu-open');
  mainArea?.classList.remove('profile-page-open');

  if (page?.parentNode && page.parentNode.contains(page)) {
    page.parentNode.removeChild(page);
  }

  window.requestAnimationFrame(() => {
    try {
      dashboardButton?.click();
      const pageScroller = document.scrollingElement || document.documentElement;
      pageScroller.scrollTo({ top: 0, behavior: 'auto' });
      window.scrollTo({ top: 0, behavior: 'auto' });
    } finally {
      window.setTimeout(() => {
        domnaiProfileClosing = false;
      }, 150);
    }
  });
}

document.addEventListener('click', safelyReturnFromProfile, true);