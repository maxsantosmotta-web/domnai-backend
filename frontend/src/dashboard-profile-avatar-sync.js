let domnaiSidebarAvatarUrl = '';
let domnaiSidebarIdentityBusy = false;
let domnaiSidebarIdentityTimer = null;

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

async function syncDomnAISidebarIdentity() {
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
    titleTarget.textContent = displayName || 'Minha conta';

    const plan = billingPayload?.premiumActive
      ? 'PREMIUM'
      : billingPayload?.plan === 'free'
        ? 'FREE'
        : 'Plano não selecionado';
    subtitleTarget.textContent = `Conta ${plan}`;

    const response = await fetch(`/api/profile/avatar?t=${Date.now()}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });

    if (!response.ok) {
      if (domnaiSidebarAvatarUrl) URL.revokeObjectURL(domnaiSidebarAvatarUrl);
      domnaiSidebarAvatarUrl = '';
      avatarTarget.innerHTML = '';
      avatarTarget.textContent = (displayName || window.Clerk?.user?.primaryEmailAddress?.emailAddress || 'U').charAt(0).toUpperCase();
      return;
    }

    const nextUrl = URL.createObjectURL(await response.blob());
    if (domnaiSidebarAvatarUrl) URL.revokeObjectURL(domnaiSidebarAvatarUrl);
    domnaiSidebarAvatarUrl = nextUrl;
    avatarTarget.innerHTML = `<img src="${nextUrl}" alt="Foto de perfil">`;
  } catch {
    // Mantém os dados já exibidos quando a sincronização não puder ser concluída.
  } finally {
    domnaiSidebarIdentityBusy = false;
  }
}

function scheduleDomnAISidebarIdentitySync(delay = 120) {
  window.clearTimeout(domnaiSidebarIdentityTimer);
  domnaiSidebarIdentityTimer = window.setTimeout(syncDomnAISidebarIdentity, delay);
}

const domnaiSidebarIdentityObserver = new MutationObserver(() => {
  if (document.querySelector('.domnai-profile-trigger')) scheduleDomnAISidebarIdentitySync();
});

domnaiSidebarIdentityObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('focus', () => scheduleDomnAISidebarIdentitySync(80));
window.addEventListener('pageshow', () => scheduleDomnAISidebarIdentitySync(80));
window.addEventListener('hashchange', () => scheduleDomnAISidebarIdentitySync(80));
window.setInterval(() => {
  if (document.querySelector('.domnai-profile-trigger')) syncDomnAISidebarIdentity();
}, 3000);

scheduleDomnAISidebarIdentitySync();
