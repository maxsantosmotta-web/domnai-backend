from pathlib import Path

onboarding_path = Path('/frontend/src/dashboard-onboarding-enhancements.js')
onboarding = onboarding_path.read_text(encoding='utf-8')
old_ready = """  if (billingHeader && plans) {
    document.documentElement.classList.remove('domnai-gate-pending');
    return;
  }
"""
new_ready = """  if (billingHeader && plans) {
    document.documentElement.classList.remove('domnai-gate-pending');
    window.dispatchEvent(new CustomEvent('domnai:plan-screen-ready'));
    return;
  }
"""
if old_ready not in onboarding:
    raise RuntimeError('Ponto de sincronização da tela de planos não encontrado.')
onboarding = onboarding.replace(old_ready, new_ready, 1)
onboarding_path.write_text(onboarding, encoding='utf-8')

billing_path = Path('/frontend/src/dashboard-billing-enhancements.js')
billing = billing_path.read_text(encoding='utf-8')
old_loader = """async function enhanceBillingScreen() {
  const sections = [...document.querySelectorAll('.internal-section')];
  const section = sections.find((item) => item.querySelector('header span')?.textContent.trim() === 'Faturamento');
  if (!section || section.dataset.billingConnected === 'true') return;
  section.dataset.billingConnected = 'true';
  section.innerHTML = '<div class=\"billing-loading-state\">Carregando informações financeiras...</div>';
  try {
    const [status, transactionPayload] = await Promise.all([billingFetch('/api/billing/status'), billingFetch('/api/billing/transactions')]);
    renderBilling(section, status, transactionPayload.items || []);
  } catch (error) {
    section.dataset.billingConnected = 'false';
    section.innerHTML = `<div class=\"billing-error-state\"><strong>Não foi possível carregar o faturamento.</strong><p>${error.message}</p><button type=\"button\">Tentar novamente</button></div>`;
    section.querySelector('button')?.addEventListener('click', () => enhanceBillingScreen());
  }
}
"""
new_loader = """async function enhanceBillingScreen() {
  const sections = [...document.querySelectorAll('.internal-section')];
  const section = sections.find((item) => item.querySelector('header span')?.textContent.trim() === 'Faturamento');
  if (!section || section.dataset.billingConnected === 'true') return;

  section.dataset.billingConnected = 'true';
  const cached = window.__domnaiBillingViewCache;
  if (cached?.status) {
    renderBilling(section, cached.status, cached.transactions || []);
  } else {
    section.innerHTML = '<div class=\"billing-loading-state\">Carregando informações financeiras...</div>';
  }

  try {
    const status = await billingFetch('/api/billing/status');
    window.__domnaiBillingStatus = status;
    window.__domnaiBillingViewCache = {
      status,
      transactions: cached?.transactions || [],
    };
    renderBilling(section, status, window.__domnaiBillingViewCache.transactions);
    window.dispatchEvent(new CustomEvent('domnai:billing-updated', { detail: status }));

    try {
      const transactionPayload = await billingFetch('/api/billing/transactions');
      const transactions = transactionPayload.items || [];
      window.__domnaiBillingViewCache = { status, transactions };
      renderBilling(section, status, transactions);
    } catch (transactionError) {
      console.error('[DomnAI] Não foi possível carregar o histórico financeiro:', transactionError);
    }
  } catch (error) {
    section.dataset.billingConnected = 'false';
    if (cached?.status) {
      renderBilling(section, cached.status, cached.transactions || []);
      return;
    }
    section.innerHTML = `<div class=\"billing-error-state\"><strong>Não foi possível carregar o faturamento.</strong><p>${error.message}</p><button type=\"button\">Tentar novamente</button></div>`;
    section.querySelector('button')?.addEventListener('click', () => enhanceBillingScreen());
  }
}
"""
if old_loader not in billing:
    raise RuntimeError('Carregador original do faturamento não encontrado.')
billing = billing.replace(old_loader, new_loader, 1)
billing_path.write_text(billing, encoding='utf-8')
