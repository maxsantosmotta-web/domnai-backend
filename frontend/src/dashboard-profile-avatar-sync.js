let domnaiSidebarAvatarUrl = '';
let domnaiSidebarAvatarBusy = false;
let domnaiSidebarAvatarTimer = null;

async function domnaiProfileAvatarToken() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session.getToken();
    await new Promise((resolve) => window.setTimeout(resolve, 120));
  }
  return '';
}

async function syncDomnAISidebarAvatar() {
  if (domnaiSidebarAvatarBusy) return;
  const target = document.querySelector('.domnai-profile-trigger-avatar');
  if (!target) return;

  domnaiSidebarAvatarBusy = true;
  try {
    const token = await domnaiProfileAvatarToken();
    if (!token) return;

    const response = await fetch(`/api/profile/avatar?t=${Date.now()}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });

    if (!response.ok) {
      if (domnaiSidebarAvatarUrl) URL.revokeObjectURL(domnaiSidebarAvatarUrl);
      domnaiSidebarAvatarUrl = '';
      if (!target.textContent.trim()) {
        target.textContent = (window.Clerk?.user?.firstName || window.Clerk?.user?.primaryEmailAddress?.emailAddress || 'U').charAt(0).toUpperCase();
      }
      return;
    }

    const nextUrl = URL.createObjectURL(await response.blob());
    if (domnaiSidebarAvatarUrl) URL.revokeObjectURL(domnaiSidebarAvatarUrl);
    domnaiSidebarAvatarUrl = nextUrl;
    target.innerHTML = `<img src="${nextUrl}" alt="Foto de perfil">`;
  } catch {
    // Mantém a inicial já exibida quando a foto não puder ser carregada.
  } finally {
    domnaiSidebarAvatarBusy = false;
  }
}

function scheduleDomnAISidebarAvatarSync(delay = 120) {
  window.clearTimeout(domnaiSidebarAvatarTimer);
  domnaiSidebarAvatarTimer = window.setTimeout(syncDomnAISidebarAvatar, delay);
}

const domnaiSidebarAvatarObserver = new MutationObserver(() => {
  if (document.querySelector('.domnai-profile-trigger-avatar')) scheduleDomnAISidebarAvatarSync();
});

domnaiSidebarAvatarObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('focus', () => scheduleDomnAISidebarAvatarSync(80));
window.addEventListener('pageshow', () => scheduleDomnAISidebarAvatarSync(80));
window.setInterval(() => {
  if (document.querySelector('[data-domnai-profile-page]')) syncDomnAISidebarAvatar();
}, 1200);

scheduleDomnAISidebarAvatarSync();
