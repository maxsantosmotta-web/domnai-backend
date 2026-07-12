const ADMIN_SYNC_KEY = 'domnai:admin-sync:v1';
const ONBOARDING_CACHE_KEY = 'domnai:onboarding-status:v1';

async function waitForClerkSession() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session;
    await new Promise((resolve) => window.setTimeout(resolve, 100));
  }
  return null;
}

async function syncOwnerAccess() {
  const session = await waitForClerkSession();
  if (!session) return;

  try {
    const token = await session.getToken();
    const response = await fetch('/api/auth/bootstrap-owner', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: '{}',
      cache: 'no-store',
    });

    if (!response.ok) {
      if (response.status !== 403) {
        const payload = await response.json().catch(() => ({}));
        console.error('[DomnAI] Falha ao sincronizar acesso administrativo:', payload.detail || response.status);
      }
      return;
    }

    const payload = await response.json();
    sessionStorage.removeItem(ONBOARDING_CACHE_KEY);
    sessionStorage.setItem(ADMIN_SYNC_KEY, JSON.stringify({
      role: payload.role,
      plan: payload.plan,
      totalCredits: payload.totalCredits,
      syncedAt: Date.now(),
    }));

    window.dispatchEvent(new CustomEvent('domnai:billing-updated', { detail: payload }));
  } catch (error) {
    console.error('[DomnAI] Erro ao sincronizar acesso administrativo:', error);
  }
}

window.addEventListener('pageshow', syncOwnerAccess, { once: true });
window.setTimeout(syncOwnerAccess, 250);
