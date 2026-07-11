function profileDigits(value) {
  return String(value || '').replace(/\D/g, '');
}

function profileFormatCpf(value) {
  const raw = profileDigits(value).slice(0, 11);
  return raw.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
}

function profileFormatPhone(value) {
  const raw = profileDigits(value).slice(0, 11);
  if (raw.length <= 10) return raw.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{4})(\d)/, '$1-$2');
  return raw.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{5})(\d)/, '$1-$2');
}

function profileFormatCep(value) {
  return profileDigits(value).slice(0, 8).replace(/(\d{5})(\d)/, '$1-$2');
}

async function profileToken() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session.getToken();
    await new Promise((resolve) => window.setTimeout(resolve, 120));
  }
  throw new Error('Sessão não encontrada.');
}

async function profileFetch(url, options = {}) {
  const token = await profileToken();
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
    throw new Error(payload.detail || 'Não foi possível concluir a operação.');
  }
  return response.json();
}

function birthParts(value) {
  const [year = '', month = '', day = ''] = String(value || '').split('-');
  return { day, month, year };
}

function profilePageHtml(profile = {}) {
  const birth = birthParts(profile.birthDate);
  const email = window.Clerk?.user?.primaryEmailAddress?.emailAddress || '';
  const initial = (profile.fullName || email || 'U').trim().charAt(0).toUpperCase();

  return `
    <section class="internal-section domnai-profile-page" data-domnai-profile-page="true">
      <header class="domnai-profile-header">
        <div>
          <span>Minha conta</span>
          <h1>Perfil do usuário</h1>
          <p>Consulte e atualize os dados cadastrados na sua conta DomnAI.</p>
        </div>
        <button type="button" class="domnai-profile-close">Voltar ao Dashboard</button>
      </header>

      <div class="domnai-profile-summary">
        <div class="domnai-profile-avatar">${initial}</div>
        <div>
          <strong>${profile.fullName || 'Perfil incompleto'}</strong>
          <span>${email || 'E-mail da conta'}</span>
        </div>
        <span class="domnai-profile-status">${profile.fullName ? 'Cadastro completo' : 'Cadastro pendente'}</span>
      </div>

      <form class="domnai-profile-form">
        <section class="domnai-profile-card">
          <div class="domnai-profile-card-title"><span>1</span><div><h2>Dados pessoais</h2><p>Informações do titular da conta.</p></div></div>
          <div class="domnai-profile-grid">
            <label class="profile-field-wide">Nome completo<input name="fullName" required maxlength="180" value="${profile.fullName || ''}"></label>
            <label>Telefone<input name="phone" required inputmode="tel" value="${profileFormatPhone(profile.phone || '')}"></label>
            <label>CPF<input name="cpf" required inputmode="numeric" value="${profileFormatCpf(profile.cpf || '')}"></label>
            <div class="domnai-birth-field profile-field-wide">
              <span>Data de nascimento</span>
              <div>
                <label>Dia<input name="birthDay" required inputmode="numeric" maxlength="2" placeholder="DD" value="${birth.day}"></label>
                <label>Mês<input name="birthMonth" required inputmode="numeric" maxlength="2" placeholder="MM" value="${birth.month}"></label>
                <label>Ano<input name="birthYear" required inputmode="numeric" maxlength="4" placeholder="AAAA" value="${birth.year}"></label>
              </div>
            </div>
          </div>
        </section>

        <section class="domnai-profile-card">
          <div class="domnai-profile-card-title"><span>2</span><div><h2>Endereço completo</h2><p>Informações vinculadas ao seu cadastro.</p></div></div>
          <div class="domnai-profile-grid">
            <label>CEP<input name="zipCode" required inputmode="numeric" value="${profileFormatCep(profile.zipCode || '')}"></label>
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
        </section>

        <p class="domnai-profile-message" hidden></p>
        <div class="domnai-profile-actions">
          <button type="button" class="secondary domnai-profile-cancel">Cancelar</button>
          <button type="submit" class="primary domnai-profile-save">Salvar alterações</button>
        </div>
      </form>
    </section>
  `;
}

function restoreDashboardFromProfile() {
  document.querySelector('[data-domnai-profile-page]')?.remove();
  document.querySelector('.domnai-main-area')?.classList.remove('profile-page-open');
  const dashboardButton = [...document.querySelectorAll('.sidebar-navigation button')]
    .find((button) => button.textContent.trim().includes('Dashboard'));
  dashboardButton?.click();
}

async function openDomnAIProfile() {
  const mainArea = document.querySelector('.domnai-main-area');
  if (!mainArea) return;

  document.querySelector('[data-domnai-profile-page]')?.remove();
  mainArea.classList.add('profile-page-open');
  mainArea.insertAdjacentHTML('beforeend', '<section class="internal-section domnai-profile-loading" data-domnai-profile-page="true">Carregando perfil...</section>');

  try {
    const payload = await profileFetch('/api/profile');
    mainArea.querySelector('[data-domnai-profile-page]')?.remove();
    mainArea.insertAdjacentHTML('beforeend', profilePageHtml(payload.profile || {}));
    bindProfilePage();
  } catch (error) {
    const page = mainArea.querySelector('[data-domnai-profile-page]');
    if (page) page.innerHTML = `<div class="internal-empty-state">${error.message}</div>`;
  }
}

function bindProfilePage() {
  const page = document.querySelector('[data-domnai-profile-page]');
  const form = page?.querySelector('.domnai-profile-form');
  if (!page || !form) return;

  page.querySelector('.domnai-profile-close')?.addEventListener('click', restoreDashboardFromProfile);
  page.querySelector('.domnai-profile-cancel')?.addEventListener('click', restoreDashboardFromProfile);

  const phone = form.elements.phone;
  const cpf = form.elements.cpf;
  const cep = form.elements.zipCode;
  phone.addEventListener('input', () => { phone.value = profileFormatPhone(phone.value); });
  cpf.addEventListener('input', () => { cpf.value = profileFormatCpf(cpf.value); });
  cep.addEventListener('input', () => { cep.value = profileFormatCep(cep.value); });
  form.elements.state.addEventListener('input', (event) => { event.target.value = event.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 2); });
  ['birthDay', 'birthMonth', 'birthYear'].forEach((name) => {
    form.elements[name].addEventListener('input', (event) => {
      event.target.value = event.target.value.replace(/\D/g, '').slice(0, Number(event.target.maxLength));
    });
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const saveButton = form.querySelector('.domnai-profile-save');
    const message = form.querySelector('.domnai-profile-message');
    const data = new FormData(form);
    const day = String(data.get('birthDay')).padStart(2, '0');
    const month = String(data.get('birthMonth')).padStart(2, '0');
    const year = String(data.get('birthYear'));

    saveButton.disabled = true;
    saveButton.textContent = 'Salvando...';
    message.hidden = true;

    try {
      await profileFetch('/api/profile', {
        method: 'PUT',
        body: JSON.stringify({
          full_name: String(data.get('fullName')).trim(),
          phone: profileDigits(data.get('phone')),
          cpf: profileDigits(data.get('cpf')),
          birth_date: `${year}-${month}-${day}`,
          zip_code: profileDigits(data.get('zipCode')),
          street: String(data.get('street')).trim(),
          number: String(data.get('number')).trim(),
          complement: String(data.get('complement')).trim(),
          lot: String(data.get('lot')).trim(),
          block: String(data.get('block')).trim(),
          building: String(data.get('building')).trim(),
          apartment: String(data.get('apartment')).trim(),
          neighborhood: String(data.get('neighborhood')).trim(),
          city: String(data.get('city')).trim(),
          state: String(data.get('state')).trim().toUpperCase(),
        }),
      });
      message.textContent = 'Dados atualizados com sucesso.';
      message.className = 'domnai-profile-message success';
      message.hidden = false;
      saveButton.textContent = 'Alterações salvas';
      window.setTimeout(openDomnAIProfile, 700);
    } catch (error) {
      message.textContent = error.message;
      message.className = 'domnai-profile-message error';
      message.hidden = false;
      saveButton.disabled = false;
      saveButton.textContent = 'Salvar alterações';
    }
  });
}

function installNativeProfileTrigger() {
  const container = document.querySelector('.sidebar-profile');
  if (!container || container.dataset.domnaiProfileReady === 'true') return;
  container.dataset.domnaiProfileReady = 'true';
  container.innerHTML = `
    <button type="button" class="domnai-profile-trigger" aria-label="Abrir Minha conta">
      <span class="domnai-profile-trigger-avatar">${(window.Clerk?.user?.firstName || window.Clerk?.user?.primaryEmailAddress?.emailAddress || 'U').charAt(0).toUpperCase()}</span>
      <span><strong>Minha conta</strong><small>Perfil e acesso</small></span>
    </button>
  `;
  container.querySelector('button')?.addEventListener('click', openDomnAIProfile);
}

const profileObserver = new MutationObserver(installNativeProfileTrigger);
profileObserver.observe(document.documentElement, { childList: true, subtree: true });
installNativeProfileTrigger();
