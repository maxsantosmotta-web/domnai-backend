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
  const labels = { plan_credit: 'Créditos do PREMIUM', extra_credit: 'Pacote avulso', consumption: 'Consumo' };
  return labels[item.kind] || item.description || 'Movimentação';
}

function normalizeApiError(detail) {
  if (!detail) return 'Não foi possível concluir a operação.';
  if (typeof detail === 'string') return detail;

  const fieldNames = {
    full_name: 'Nome completo',
    phone: 'Telefone',
    cpf: 'CPF',
    birth_date: 'Data de nascimento',
    zip_code: 'CEP',
    street: 'Rua',
    number: 'Número',
    neighborhood: 'Bairro',
    city: 'Cidade',
    state: 'Estado',
  };

  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === 'string') return item;
      const location = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : '';
      const field = fieldNames[location] || location || 'Campo';
      const message = item?.msg || 'valor inválido';
      return `${field}: ${message}`;
    }).join(' · ');
  }

  if (typeof detail === 'object') {
    return detail.message || detail.msg || JSON.stringify(detail);
  }

  return String(detail);
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
    throw new Error(normalizeApiError(payload.detail || payload.message));
  }
  return response.status === 204 ? null : response.json();
}

function statusBadge(status) {
  const labels = { active: 'Ativo', trialing: 'Ativo', past_due: 'Pagamento pendente', canceled: 'Cancelado', unpaid: 'Inadimplente', inactive: 'Inativo' };
  return labels[status] || 'Inativo';
}

function premiumBenefits() {
  return `
    <ul class="billing-benefits-list">
      <li>Acesso completo às operações</li>
      <li>Chat com análises e respostas</li>
      <li>Envio de PDF, link, print, imagem e documentos</li>
      <li>Biblioteca e Lixeira</li>
      <li>500 créditos por ciclo</li>
      <li>Compra de créditos avulsos</li>
    </ul>
  `;
}

function digits(value) {
  return String(value || '').replace(/\D/g, '');
}

function safeText(value) {
  return String(value || '').trim();
}

function formatCpf(value) {
  const raw = digits(value).slice(0, 11);
  return raw.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
}

function formatPhone(value) {
  const raw = digits(value).slice(0, 11);
  if (raw.length <= 10) return raw.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{4})(\d)/, '$1-$2');
  return raw.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{5})(\d)/, '$1-$2');
}

function formatCep(value) {
  return digits(value).slice(0, 8).replace(/(\d{5})(\d)/, '$1-$2');
}

function profileFormHtml(profile = {}, actionLabel = 'Continuar') {
  return `
    <div class="profile-checklist-overlay" role="dialog" aria-modal="true" aria-label="Complete seu cadastro">
      <section class="profile-checklist-card">
        <header>
          <span>Cadastro obrigatório</span>
          <h2>Complete seu perfil</h2>
          <p>Preencha seus dados uma única vez. Depois, você poderá atualizá-los em Minha conta.</p>
        </header>
        <form class="profile-checklist-form">
          <div class="profile-checklist-step"><span>1</span><div><strong>Dados pessoais</strong><small>Identificação do titular da conta</small></div></div>
          <div class="profile-form-grid">
            <label class="profile-field-wide">Nome completo<input name="fullName" required maxlength="180" value="${profile.fullName || ''}"></label>
            <label>Telefone<input name="phone" required inputmode="tel" value="${profile.phone || ''}"></label>
            <label>CPF<input name="cpf" required inputmode="numeric" value="${profile.cpf || ''}"></label>
            <label>Data de nascimento<input name="birthDate" required type="date" value="${profile.birthDate || ''}"></label>
          </div>

          <div class="profile-checklist-step"><span>2</span><div><strong>Endereço completo</strong><small>Informações para identificação e cobrança</small></div></div>
          <div class="profile-form-grid">
            <label>CEP<input name="zipCode" required inputmode="numeric" value="${profile.zipCode || ''}"></label>
            <label class="profile-field-wide">Rua<input name="street" required maxlength="180" value="${profile.street || ''}"></label>
            <label>Número<input name="number" required maxlength="30" value="${profile.number || ''}"></label>
            <label>Complemento <small>opcional</small><input name="complement" maxlength="120" value="${profile.complement || ''}"></label>
            <label>Lote <small>opcional</small><input name="lot" maxlength="30" value="${profile.lot || ''}"></label>
            <label>Quadra <small>opcional</small><input name="block" maxlength="30" value="${profile.block || ''}"></label>
            <label>Bloco <small>opcional</small><input name="building" maxlength="30" value="${profile.building || ''}"></label>
            <label>Apartamento <small>opcional</small><input name="apartment" maxlength="30" value="${profile.apartment || ''}"></label>
            <label>Bairro<input name="neighborhood" required maxlength="120" value="${profile.neighborhood || ''}"></label>
            <label>Cidade<input name="city" required maxlength="120" value="${profile.city || ''}"></label>
            <label>Estado<input name="state" required maxlength="2" value="${profile.state || ''}"></label>
          </div>
          <p class="profile-checklist-error" hidden></p>
          <div class="profile-checklist-actions">
            <button type="button" class="profile-checklist-cancel">Voltar</button>
            <button type="submit" class="profile-checklist-submit">${actionLabel}</button>
          </div>
        </form>
      </section>
    </div>
  `;
}

async function openProfileChecklist(onComplete, actionLabel) {
  if (document.querySelector('.profile-checklist-overlay')) return;
  window.dispatchEvent(new CustomEvent('domnai:onboarding-profile-opened'));

  let profile = {};
  try {
    const payload = await billingFetch('/api/profile');
    profile = payload.profile || {};
  } catch {
    profile = {};
  }

  document.body.insertAdjacentHTML('beforeend', profileFormHtml(profile, actionLabel));
  const overlay = document.querySelector('.profile-checklist-overlay');
  const form = overlay.querySelector('form');
  const errorBox = overlay.querySelector('.profile-checklist-error');
  const submit = overlay.querySelector('.profile-checklist-submit');

  const cpf = form.elements.cpf;
  const phone = form.elements.phone;
  const cep = form.elements.zipCode;
  cpf.value = formatCpf(cpf.value);
  phone.value = formatPhone(phone.value);
  cep.value = formatCep(cep.value);
  cpf.addEventListener('input', () => { cpf.value = formatCpf(cpf.value); });
  phone.addEventListener('input', () => { phone.value = formatPhone(phone.value); });
  cep.addEventListener('input', () => { cep.value = formatCep(cep.value); });
  form.elements.state.addEventListener('input', (event) => { event.target.value = event.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 2); });

  overlay.querySelector('.profile-checklist-cancel').addEventListener('click', () => {
    overlay.remove();
    window.dispatchEvent(new CustomEvent('domnai:onboarding-profile-cancelled'));
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorBox.hidden = true;

    const data = new FormData(form);
    const day = safeText(data.get('birthDay')).padStart(2, '0');
    const month = safeText(data.get('birthMonth')).padStart(2, '0');
    const year = safeText(data.get('birthYear'));
    const birthDate = safeText(data.get('birthDate')) || (day && month && year.length === 4 ? `${year}-${month}-${day}` : '');

    const requiredChecks = [
      ['Nome completo', safeText(data.get('fullName'))],
      ['Telefone', digits(data.get('phone'))],
      ['CPF', digits(data.get('cpf'))],
      ['Data de nascimento', birthDate],
      ['CEP', digits(data.get('zipCode'))],
      ['Rua', safeText(data.get('street'))],
      ['Número', safeText(data.get('number'))],
      ['Bairro', safeText(data.get('neighborhood'))],
      ['Cidade', safeText(data.get('city'))],
      ['Estado', safeText(data.get('state'))],
    ];
    const missing = requiredChecks.filter(([, value]) => !value).map(([label]) => label);

    if (missing.length) {
      errorBox.textContent = `Preencha os campos obrigatórios: ${missing.join(', ')}.`;
      errorBox.hidden = false;
      return;
    }

    submit.disabled = true;
    submit.textContent = 'Salvando cadastro...';

    const body = {
      full_name: safeText(data.get('fullName')),
      phone: digits(data.get('phone')),
      cpf: digits(data.get('cpf')),
      birth_date: birthDate,
      zip_code: digits(data.get('zipCode')),
      street: safeText(data.get('street')),
      number: safeText(data.get('number')),
      complement: safeText(data.get('complement')),
      lot: safeText(data.get('lot')),
      block: safeText(data.get('block')),
      building: safeText(data.get('building')),
      apartment: safeText(data.get('apartment')),
      neighborhood: safeText(data.get('neighborhood')),
      city: safeText(data.get('city')),
      state: safeText(data.get('state')).toUpperCase(),
    };

    try {
      await billingFetch('/api/profile', { method: 'PUT', body: JSON.stringify(body) });
      await onComplete();
      overlay.remove();
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
      submit.disabled = false;
      submit.textContent = actionLabel;
    }
  });
}

async function ensureProfileThen(status, action, actionLabel) {
  if (status.profileCompleted) return action();
  return openProfileChecklist(action, actionLabel);
}

function renderBilling(section, status, transactions, selectedPeriod = 'monthly') {
  const premium = Boolean(status.premiumActive);
  const freeSelected = status.plan === 'free';
  const noPlan = !premium && !freeSelected;
  const total = Number(status.totalCredits || 0);
  const planCredits = Number(status.planCredits || 0);
  const extraCredits = Number(status.extraCredits || 0);
  const annual = selectedPeriod === 'yearly';
  const currentPlanName = premium ? 'PREMIUM' : freeSelected ? 'FREE' : 'Nenhum plano selecionado';
  const currentPlanDescription = premium
    ? `Status: ${statusBadge(status.subscriptionStatus)}${status.currentPeriodEnd ? ` · válido até ${moneyDate(status.currentPeriodEnd)}` : ''}`
    : freeSelected ? 'Navegação e visualização da plataforma.' : 'Escolha uma opção abaixo para continuar.';

  section.innerHTML = `
    <header class="billing-page-header">
      <div><span>Faturamento</span><h1>Plano e créditos</h1><p>Acompanhe seu saldo, assinatura e pacotes adicionais.</p></div>
      <button type="button" class="billing-back-to-chat" data-billing-action="back-to-chat" aria-label="Voltar ao chat"><span>←</span><span class="billing-back-label">Voltar ao chat</span></button>
    </header>
    <div class="billing-balance-grid">
      <article class="billing-balance-card billing-balance-primary"><small>Saldo disponível</small><strong>${total}</strong><span>créditos</span></article>
      <article class="billing-balance-card"><small>Créditos do plano</small><strong>${planCredits}</strong><span>renovados por ciclo</span></article>
      <article class="billing-balance-card"><small>Créditos avulsos</small><strong>${extraCredits}</strong><span>não expiram</span></article>
    </div>
    <section class="billing-current-plan${noPlan ? ' billing-current-plan-empty' : ''}"><div><small>Plano atual</small><h2>${currentPlanName}</h2><p>${currentPlanDescription}</p></div>${premium ? '<button type="button" data-billing-action="portal">Gerenciar assinatura</button>' : ''}</section>

    <section class="billing-plans-section">
      <div class="billing-section-title"><small>Planos</small><h2>Escolha seu acesso</h2></div>
      <div class="billing-plan-grid billing-plan-grid-two">
        <article class="billing-plan-card billing-free-card${freeSelected ? ' billing-plan-selected' : ''}">
          <span class="billing-plan-tag">Grátis</span><h3>FREE</h3><strong>R$ 0</strong><p>Navegação e visualização da plataforma.</p>
          <button type="button" class="billing-free-button" data-billing-action="free" ${freeSelected ? 'disabled' : ''}>${freeSelected ? 'Plano atual' : 'Escolher FREE'}</button>
        </article>
        <article class="billing-plan-card billing-plan-featured billing-premium-card">
          <div class="billing-premium-heading">
            <div><span class="billing-plan-tag">PREMIUM</span><h3>PREMIUM</h3></div>
            <div class="billing-period-switch" role="group" aria-label="Período da assinatura">
              <button type="button" data-billing-period="monthly" class="${annual ? '' : 'is-active'}">Mensal</button>
              <button type="button" data-billing-period="yearly" class="${annual ? 'is-active' : ''}">Anual${annual ? '<span>Economize 17%</span>' : ''}</button>
            </div>
          </div>
          <strong>${annual ? 'R$ 599,00 <small>/ano</small>' : 'R$ 59,90 <small>/mês</small>'}</strong>
          <p class="billing-period-copy">${annual ? 'Cobrança anual com 500 créditos renovados mensalmente.' : 'Cobrança mensal com 500 créditos por ciclo.'}</p>
          ${premiumBenefits()}
          <button type="button" data-billing-product="${annual ? BILLING_PRODUCTS.yearly : BILLING_PRODUCTS.monthly}">Assinar PREMIUM</button>
        </article>
      </div>
    </section>

    <section class="billing-extra-section"><div><small>Pacote avulso</small><h2 class="billing-extra-price">R$ 25,00</h2><strong class="billing-extra-credits">250 créditos</strong><p>Compre quantas vezes quiser · os créditos não expiram.</p></div><button type="button" data-billing-product="${BILLING_PRODUCTS.credits}">COMPRAR 🛒</button></section>
    <section class="billing-rules-section"><div class="billing-section-title"><small>Consumo</small><h2>Créditos por utilização</h2></div><div class="billing-rules-grid"><span><strong>1 crédito</strong> Pergunta com resposta</span><span><strong>2 créditos</strong> Análise completa</span><span><strong>5 a 10 créditos</strong> PDF, link, print, imagem ou documento</span></div></section>
    <section class="billing-history-section"><div class="billing-section-title"><small>Histórico</small><h2>Movimentações</h2></div><div class="billing-history-list">${transactions.length ? transactions.map((item) => `<article><div><strong>${transactionLabel(item)}</strong><small>${new Date(item.createdAt).toLocaleString('pt-BR')}</small></div><span class="${item.amount >= 0 ? 'credit-positive' : 'credit-negative'}">${item.amount >= 0 ? '+' : ''}${item.amount}</span></article>`).join('') : '<p class="billing-empty-history">Nenhuma movimentação registrada ainda.</p>'}</div></section>
  `;

  section.querySelector('[data-billing-action="back-to-chat"]')?.addEventListener('click', () => {
    const globalExit = document.querySelector('.global-exit-button');
    if (globalExit) {
      globalExit.click();
      return;
    }
    window.location.hash = '#/';
  });

  section.querySelectorAll('[data-billing-period]').forEach((button) => button.addEventListener('click', () => renderBilling(section, status, transactions, button.dataset.billingPeriod)));

  section.querySelectorAll('[data-billing-product]').forEach((button) => {
    button.addEventListener('click', async () => {
      const product = button.dataset.billingProduct;
      const checkoutAction = async () => {
        const original = button.textContent;
        button.disabled = true;
        button.textContent = 'Abrindo checkout...';
        try {
          const result = await billingFetch('/api/billing/checkout', { method: 'POST', body: JSON.stringify({ product }) });
          window.location.assign(result.url);
        } catch (error) {
          window.alert(error.message);
          button.disabled = false;
          button.textContent = original;
        }
      };
      if (product === BILLING_PRODUCTS.credits) return checkoutAction();
      return ensureProfileThen(status, checkoutAction, 'Continuar para o pagamento');
    });
  });

  section.querySelector('[data-billing-action="free"]:not([disabled])')?.addEventListener('click', () => {
    const activateFree = async () => {
      const updatedStatus = await billingFetch('/api/billing/select-free', { method: 'POST', body: '{}' });
      renderBilling(section, updatedStatus, transactions, selectedPeriod);
      window.dispatchEvent(new CustomEvent('domnai:billing-updated', { detail: updatedStatus }));
      return updatedStatus;
    };
    ensureProfileThen(status, activateFree, 'Ativar plano FREE').catch((error) => window.alert(error.message));
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
    const [status, transactionPayload] = await Promise.all([billingFetch('/api/billing/status'), billingFetch('/api/billing/transactions')]);
    renderBilling(section, status, transactionPayload.items || []);
  } catch (error) {
    section.dataset.billingConnected = 'false';
    section.innerHTML = `<div class="billing-error-state"><strong>Não foi possível carregar o faturamento.</strong><p>${error.message}</p><button type="button">Tentar novamente</button></div>`;
    section.querySelector('button')?.addEventListener('click', () => enhanceBillingScreen());
  }
}

const billingObserver = new MutationObserver(() => window.requestAnimationFrame(enhanceBillingScreen));
billingObserver.observe(document.documentElement, { childList: true, subtree: true });
window.addEventListener('hashchange', () => window.setTimeout(enhanceBillingScreen, 50));
enhanceBillingScreen();
