const BILLING_PRODUCTS = {
  monthly: 'premium_monthly',
  yearly: 'premium_yearly',
  credits: 'credits_250',
};

function moneyDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('pt-BR');
}

function transactionLabel(item) {
  const labels = {
    plan_credit: 'Créditos do Premium',
    extra_credit: 'Pacote avulso',
    consumption: 'Consumo',
  };
  return labels[item.kind] || item.description || 'Movimentação';
}

async function getAuthToken() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const clerk = window.Clerk;
    if (clerk?.session) return clerk.session.getToken();
    await new Promise((resolve) => window.setTimeout(resolve, 150));
  }
  throw new Error('Sessão não encontrada. Atualize a página e tente novamente.');
}

async function billingFetch(url, options = {}) {
  const token = await getAuthToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || 'Não foi possível concluir a operação financeira.');
  }

  return response.status === 204 ? null : response.json();
}

function statusBadge(status) {
  const labels = {
    active: 'Ativo',
    trialing: 'Ativo',
    past_due: 'Pagamento pendente',
    canceled: 'Cancelado',
    unpaid: 'Inadimplente',
    inactive: 'Free Demo',
  };
  return labels[status] || 'Free Demo';
}

function renderBilling(section, status, transactions) {
  const premium = Boolean(status.premiumActive);
  const total = Number(status.totalCredits || 0);
  const planCredits = Number(status.planCredits || 0);
  const extraCredits = Number(status.extraCredits || 0);

  section.innerHTML = `
    <header class="billing-page-header">
      <div>
        <span>Faturamento</span>
        <h1>Plano e créditos</h1>
        <p>Acompanhe seu saldo, assinatura e pacotes adicionais.</p>
      </div>
    </header>

    <div class="billing-balance-grid">
      <article class="billing-balance-card billing-balance-primary">
        <small>Saldo disponível</small>
        <strong>${total}</strong>
        <span>créditos</span>
      </article>
      <article class="billing-balance-card">
        <small>Créditos do plano</small>
        <strong>${planCredits}</strong>
        <span>renovados por ciclo</span>
      </article>
      <article class="billing-balance-card">
        <small>Créditos avulsos</small>
        <strong>${extraCredits}</strong>
        <span>não expiram</span>
      </article>
    </div>

    <section class="billing-current-plan">
      <div>
        <small>Plano atual</small>
        <h2>${premium ? 'Premium' : 'Free Demo'}</h2>
        <p>${premium ? `Status: ${statusBadge(status.subscriptionStatus)}${status.currentPeriodEnd ? ` · válido até ${moneyDate(status.currentPeriodEnd)}` : ''}` : 'Explore a plataforma e assine para usar as operações, análises e arquivos.'}</p>
      </div>
      ${premium ? '<button type="button" data-billing-action="portal">Gerenciar assinatura</button>' : ''}
    </section>

    <section class="billing-plans-section">
      <div class="billing-section-title">
        <small>Premium</small>
        <h2>Escolha sua assinatura</h2>
      </div>
      <div class="billing-plan-grid">
        <article class="billing-plan-card">
          <span class="billing-plan-tag">Mensal</span>
          <h3>Premium</h3>
          <strong>R$ 59,90 <small>/mês</small></strong>
          <p>500 créditos a cada ciclo mensal.</p>
          <button type="button" data-billing-product="${BILLING_PRODUCTS.monthly}">${premium ? 'Trocar para mensal' : 'Assinar mensal'}</button>
        </article>
        <article class="billing-plan-card billing-plan-featured">
          <span class="billing-plan-tag">Anual</span>
          <h3>Premium</h3>
          <strong>R$ 599,00 <small>/ano</small></strong>
          <p>500 créditos renovados mensalmente durante o plano anual.</p>
          <button type="button" data-billing-product="${BILLING_PRODUCTS.yearly}">${premium ? 'Trocar para anual' : 'Assinar anual'}</button>
        </article>
      </div>
    </section>

    <section class="billing-extra-section">
      <div>
        <small>Pacote avulso</small>
        <h2>250 créditos adicionais</h2>
        <p>R$ 25,00 · compre quantas vezes quiser · os créditos não expiram.</p>
      </div>
      <button type="button" data-billing-product="${BILLING_PRODUCTS.credits}">COMPRAR 🛒</button>
    </section>

    <section class="billing-rules-section">
      <div class="billing-section-title">
        <small>Como os créditos são consumidos</small>
        <h2>Valores por utilização</h2>
      </div>
      <div class="billing-rules-grid">
        <span><strong>1 crédito</strong> Pergunta com resposta</span>
        <span><strong>2 créditos</strong> Análise completa</span>
        <span><strong>5 a 10 créditos</strong> PDF, link, print, imagem ou documento</span>
      </div>
    </section>

    <section class="billing-history-section">
      <div class="billing-section-title">
        <small>Histórico</small>
        <h2>Movimentações recentes</h2>
      </div>
      <div class="billing-history-list">
        ${transactions.length ? transactions.map((item) => `
          <article>
            <div>
              <strong>${transactionLabel(item)}</strong>
              <small>${new Date(item.createdAt).toLocaleString('pt-BR')}</small>
            </div>
            <span class="${item.amount >= 0 ? 'credit-positive' : 'credit-negative'}">${item.amount >= 0 ? '+' : ''}${item.amount}</span>
          </article>
        `).join('') : '<p class="billing-empty-history">Nenhuma movimentação registrada ainda.</p>'}
      </div>
    </section>
  `;

  section.querySelectorAll('[data-billing-product]').forEach((button) => {
    button.addEventListener('click', async () => {
      const original = button.textContent;
      button.disabled = true;
      button.textContent = 'Abrindo checkout...';
      try {
        const result = await billingFetch('/api/billing/checkout', {
          method: 'POST',
          body: JSON.stringify({ product: button.dataset.billingProduct }),
        });
        window.location.assign(result.url);
      } catch (error) {
        window.alert(error.message);
        button.disabled = false;
        button.textContent = original;
      }
    });
  });

  section.querySelector('[data-billing-action="portal"]')?.addEventListener('click', async (event) => {
    const button = event.currentTarget;
    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Abrindo...';
    try {
      const result = await billingFetch('/api/billing/portal', { method: 'POST', body: '{}' });
      window.location.assign(result.url);
    } catch (error) {
      window.alert(error.message);
      button.disabled = false;
      button.textContent = original;
    }
  });
}

async function enhanceBillingScreen() {
  const sections = [...document.querySelectorAll('.internal-section')];
  const section = sections.find((item) => item.querySelector('header span')?.textContent.trim() === 'Faturamento');
  if (!section || section.dataset.billingConnected === 'true') return;

  section.dataset.billingConnected = 'true';
  section.innerHTML = '<div class="billing-loading-state">Carregando informações financeiras...</div>';

  try {
    const [status, transactionPayload] = await Promise.all([
      billingFetch('/api/billing/status'),
      billingFetch('/api/billing/transactions'),
    ]);
    renderBilling(section, status, transactionPayload.items || []);
  } catch (error) {
    section.dataset.billingConnected = 'false';
    section.innerHTML = `<div class="billing-error-state"><strong>Não foi possível carregar o faturamento.</strong><p>${error.message}</p><button type="button">Tentar novamente</button></div>`;
    section.querySelector('button')?.addEventListener('click', () => enhanceBillingScreen());
  }
}

const billingObserver = new MutationObserver(() => {
  window.requestAnimationFrame(enhanceBillingScreen);
});

billingObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.setTimeout(enhanceBillingScreen, 50));
enhanceBillingScreen();
