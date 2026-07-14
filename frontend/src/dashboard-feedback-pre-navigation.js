function closeFeedbackBeforeProfile(event) {
  const profileTrigger = event.target.closest('.domnai-profile-trigger, .sidebar-profile');
  if (!profileTrigger) return;

  document.querySelector('[data-domnai-feedback-page="true"]')?.remove();
  document.querySelector('.domnai-main-area')?.classList.remove('feedback-page-open');
  document.querySelector('[data-domnai-feedback-menu="true"]')?.classList.remove('is-active');
}

document.addEventListener('click', closeFeedbackBeforeProfile, true);
