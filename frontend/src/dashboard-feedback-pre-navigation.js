function closeFeedbackBeforeProfile(event) {
  const profileTrigger = event.target.closest('.domnai-profile-trigger, .sidebar-profile');
  if (!profileTrigger) return;

  document.querySelector('[data-domnai-feedback-page="true"]')?.remove();
  document.querySelector('.domnai-main-area')?.classList.remove('feedback-page-open');
  document.querySelector('[data-domnai-feedback-menu="true"]')?.classList.remove('is-active');
}

function installFeedbackPremiumVisualGuard() {
  if (document.querySelector('[data-domnai-feedback-premium-visual-guard]')) return;

  const style = document.createElement('style');
  style.dataset.domnaiFeedbackPremiumVisualGuard = 'true';
  style.textContent = `
    .domnai-feedback-menu-button .domnai-feedback-menu-label,
    .domnai-feedback-menu-button:hover .domnai-feedback-menu-label,
    .domnai-feedback-menu-button:focus .domnai-feedback-menu-label,
    .domnai-feedback-menu-button:active .domnai-feedback-menu-label,
    .domnai-feedback-menu-button.is-active .domnai-feedback-menu-label,
    .domnai-feedback-menu-button.is-premium-locked .domnai-feedback-menu-label {
      color: #ffffff !important;
    }

    .domnai-feedback-menu-button.is-premium-locked,
    .domnai-feedback-menu-button.is-premium-locked:hover,
    .domnai-feedback-menu-button.is-premium-locked:focus,
    .domnai-feedback-menu-button.is-premium-locked:active {
      border-color: transparent !important;
      background: transparent !important;
      box-shadow: none !important;
    }

    .domnai-feedback-menu-button > small {
      pointer-events: none !important;
      color: #e7c35e !important;
    }

    .domnai-feedback-premium-notice,
    [data-feedback-premium-notice] {
      display: none !important;
    }
  `;
  document.head.appendChild(style);
}

document.addEventListener('click', closeFeedbackBeforeProfile, true);
installFeedbackPremiumVisualGuard();
