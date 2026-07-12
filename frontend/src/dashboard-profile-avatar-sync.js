let domnaiSidebarAvatarUrl = '';
let domnaiSidebarIdentityBusy = false;
let domnaiSidebarIdentityTimer = null;
let domnaiSidebarIdentityLoaded = false;

async function domnaiProfileIdentityToken() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session.getToken();
    await new Promise((resolve) => window.setTimeout(resolve, 120));
  }
  return '';
}

function domnaiCompactName(value) {
  const parts = String(value || '').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '';
  if (parts.length === 1) return parts[0];
  return `${parts[0]} ${parts[parts.length - 1]}`;
}

async function domnaiFetchJson(url, token) {
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });
  if (!response.ok) return null;
  return response.json();
}

function renderSidebarInitial(avatarTarget, displayName) {
  if (avatarTarget.querySelector('img')) return;
  avatarTarget.textContent = (displayName || window.Clerk?.user?.primaryEmailAddress?.emailAddress || 'U').charAt(0).toUpperCase();
}

async function syncDomnAISidebarIdentity({ forceAvatar = false } = {}) {
  if (domnaiSidebarIdentityBusy) return;

  const trigger = document.querySelector('.domnai-profile-trigger');
  const avatarTarget = trigger?.querySelector('.domnai-profile-trigger-avatar');
  const titleTarget = trigger?.querySelector('strong');
  const subtitleTarget = trigger?.querySelector('small');
  if (!trigger || !avatarTarget || !titleTarget || !subtitleTarget) return;

  domnaiSidebarIdentityBusy = true;
  try {
    const token = await domnaiProfileIdentityToken();
    if (!token) return;

    const [profilePayload, billingPayload] = await Promise.all([
      domnaiFetchJson('/api/profile', token),
      domnaiFetchJson('/api/billing/status', token),
    ]);

    const fullName = profilePayload?.profile?.fullName || window.Clerk?.user?.fullName || window.Clerk?.user?.firstName || '';
    const displayName = domnaiCompactName(fullName);
    const nextTitle = displayName || 'Minha conta';
    const plan = billingPayload?.premiumActive
      ? 'PREMIUM'
      : billingPayload?.plan === 'free'
        ? 'FREE'
        : 'Plano não selecionado';
    const nextSubtitle = `Conta ${plan}`;

    if (titleTarget.textContent !== nextTitle) titleTarget.textContent = nextTitle;
    if (subtitleTarget.textContent !== nextSubtitle) subtitleTarget.textContent = nextSubtitle;

    if (domnaiSidebarIdentityLoaded && !forceAvatar) return;

    const response = await fetch('/api/profile/avatar', {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });

    if (!response.ok) {
      renderSidebarInitial(avatarTarget, displayName);
      domnaiSidebarIdentityLoaded = true;
      return;
    }

    const nextUrl = URL.createObjectURL(await response.blob());
    const image = avatarTarget.querySelector('img');

    if (image) {
      image.src = nextUrl;
    } else {
      avatarTarget.textContent = '';
      const nextImage = document.createElement('img');
      nextImage.src = nextUrl;
      nextImage.alt = 'Foto de perfil';
      avatarTarget.appendChild(nextImage);
    }

    if (domnaiSidebarAvatarUrl) URL.revokeObjectURL(domnaiSidebarAvatarUrl);
    domnaiSidebarAvatarUrl = nextUrl;
    domnaiSidebarIdentityLoaded = true;
  } catch {
    // Mantém a identidade já exibida quando a sincronização não puder ser concluída.
  } finally {
    domnaiSidebarIdentityBusy = false;
  }
}

function scheduleDomnAISidebarIdentitySync(delay = 120, options = {}) {
  window.clearTimeout(domnaiSidebarIdentityTimer);
  domnaiSidebarIdentityTimer = window.setTimeout(() => syncDomnAISidebarIdentity(options), delay);
}

const domnaiSidebarIdentityObserver = new MutationObserver(() => {
  if (document.querySelector('.domnai-profile-trigger') && !domnaiSidebarIdentityLoaded) {
    scheduleDomnAISidebarIdentitySync();
  }
});

domnaiSidebarIdentityObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => scheduleDomnAISidebarIdentitySync(80));
window.addEventListener('domnai:profile-avatar-updated', () => {
  domnaiSidebarIdentityLoaded = false;
  scheduleDomnAISidebarIdentitySync(40, { forceAvatar: true });
});

scheduleDomnAISidebarIdentitySync();
