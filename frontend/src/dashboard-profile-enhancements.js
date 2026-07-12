const DOMNAI_PROFILE_CACHE_KEY = 'domnai:profile:v1';
let domnaiProfileMemory = null;
let domnaiProfileAvatarMemory = '';
let domnaiProfileRefreshing = false;

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

function readProfileCache() {
  if (domnaiProfileMemory) return domnaiProfileMemory;
  try {
    const cached = JSON.parse(sessionStorage.getItem(DOMNAI_PROFILE_CACHE_KEY) || 'null');
    if (cached?.profile) domnaiProfileMemory = cached.profile;
  } catch {
    // Cache é apenas uma otimização.
  }
  return domnaiProfileMemory;
}

function writeProfileCache(profile) {
  domnaiProfileMemory = profile || {};
  try {
    sessionStorage.setItem(DOMNAI_PROFILE_CACHE_KEY, JSON.stringify({ profile: domnaiProfileMemory, savedAt: Date.now() }));
  } catch {
    // Cache é apenas uma otimização.
  }
}

function currentSidebarAvatarUrl() {
  return document.querySelector('.domnai-profile-trigger-avatar img')?.src || domnaiProfileAvatarMemory || '';
}

async function profileToken() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session.getToken();
    await new Promise((resolve) => window.setTimeout(resolve, 75));
  }
  throw new Error('Sessão não encontrada.');
}

async function profileFetch(url, options = {}) {
  const token = await profileToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item?.msg || 'Dado inválido').join(' · ')
      : typeof detail === 'string' ? detail : 'Não foi possível concluir a operação.';
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function profileAvatarUrl() {
  try {
    const token = await profileToken();
    const response = await fetch('/api/profile/avatar', {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!response.ok) return '';
    const nextUrl = URL.createObjectURL(await response.blob());
    if (domnaiProfileAvatarMemory && domnaiProfileAvatarMemory.startsWith('blob:')) URL.revokeObjectURL(domnaiProfileAvatarMemory);
    domnaiProfileAvatarMemory = nextUrl;
    return nextUrl;
  } catch {
    return currentSidebarAvatarUrl();
  }
}

function birthParts(value) {
  const [year = '', month = '', day = ''] = String(value || '').split('-');
  return { day, month, year };
}

function profilePageHtml(profile = {}, avatarUrl = '') {
  const birth = birthParts(profile.birthDate);
  const email = window.Clerk?.user?.primaryEmailAddress?.emailAddress || '';
  const initial = (profile.fullName || email || 'U').trim().charAt(0).toUpperCase();
  const avatar = avatarUrl ? `<img src="${avatarUrl}" alt="Foto de perfil">` : `<span>${initial}</span>`;

  return `
    <section class="internal-section domnai-profile-page" data-domnai-profile-page="true">
      <header class="domnai-profile-header">
        <div><span>Minha conta</span><h1>Perfil do usuário</h1><p>Consulte e atualize os dados cadastrados na sua conta DomnAI.</p></div>
        <button type="button" class="domnai-profile-close">Voltar ao Dashboard</button>
      </header>
      <div class="domnai-profile-summary">
        <div class="domnai-profile-photo-wrap">
          <div class="domnai-profile-avatar">${avatar}</div>
          <label class="domnai-profile-photo-button">Alterar foto<input type="file" accept="image/jpeg,image/png,image/webp" class="domnai-profile-photo-input"></label>
          ${avatarUrl ? '<button type="button" class="domnai-profile-photo-remove">Remover</button>' : ''}
        </div>
        <div><strong>${profile.fullName || 'Perfil incompleto'}</strong><span>${email || 'E-mail da conta'}</span><small>JPG, PNG ou WEBP · até 5 MB</small></div>
        <span class="domnai-profile-status">${profile.fullName ? 'Cadastro completo' : 'Cadastro pendente'}</span>
      </div>
      <form class="domnai-profile-form">
        <section class="domnai-profile-card">
          <div class="domnai-profile-card-title"><span>1</span><div><h2>Dados pessoais</h2><p>Informações do titular da conta.</p></div></div>
          <div class="domnai-profile-grid">
            <label class="profile-field-wide">Nome completo<input name="fullName" required maxlength="180" value="${profile.fullName || ''}"></label>
            <label>Telefone<input name="phone" required inputmode="tel" value="${profileFormatPhone(profile.phone || '')}"></label>
            <label>CPF<input name="cpf" required inputmode="numeric" value="${profileFormatCpf(profile.cpf || '')}"></label>
            <div class="domnai-birth-field profile-field-wide"><span>Data de nascimento</span><div>
              <label>Dia<input name="birthDay" required inputmode="numeric" maxlength="2" value="${birth.day}"></label>
              <label>Mês<input name="birthMonth" required inputmode="numeric" maxlength="2" value="${birth.month}"></label>
              <label>Ano<input name="birthYear" required inputmode="numeric" maxlength="4" value="${birth.year}"></label>
            </div></div>
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
        <div class="domnai-profile-actions"><button type="button" class="secondary domnai-profile-cancel">Cancelar</button><button type="submit" class="primary domnai-profile-save">Salvar alterações</button></div>
      </form>
    </section>`;
}

function restoreDashboardFromProfile() {
  document.querySelector('[data-domnai-profile-page]')?.remove();
  document.querySelector('.domnai-main-area')?.classList.remove('profile-page-open');
  [...document.querySelectorAll('.sidebar-navigation button')].find((button) => button.textContent.trim().includes('Dashboard'))?.click();
}

function renderProfileImmediately(profile, avatarUrl) {
  const mainArea = document.querySelector('.domnai-main-area');
  if (!mainArea) return;
  mainArea.querySelector('[data-domnai-profile-page]')?.remove();
  mainArea.insertAdjacentHTML('beforeend', profilePageHtml(profile || {}, avatarUrl || ''));
  bindProfilePage();
}

async function refreshDomnAIProfileSilently() {
  if (domnaiProfileRefreshing) return;
  domnaiProfileRefreshing = true;
  try {
    const payload = await profileFetch('/api/profile');
    const profile = payload?.profile || {};
    writeProfileCache(profile);

    const page = document.querySelector('[data-domnai-profile-page]');
    if (!page) return;

    const currentForm = page.querySelector('.domnai-profile-form');
    const editing = currentForm && [...currentForm.elements].some((element) => element === document.activeElement);
    if (!editing) renderProfileImmediately(profile, currentSidebarAvatarUrl());

    profileAvatarUrl().then((avatarUrl) => {
      const avatar = document.querySelector('[data-domnai-profile-page] .domnai-profile-avatar');
      if (!avatar || !avatarUrl) return;
      avatar.innerHTML = `<img src="${avatarUrl}" alt="Foto de perfil">`;
    });
  } catch {
    // Mantém o perfil em cache sem interromper a navegação.
  } finally {
    domnaiProfileRefreshing = false;
  }
}

async function openDomnAIProfile() {
  const mainArea = document.querySelector('.domnai-main-area');
  if (!mainArea) return;

  document.querySelector('[data-domnai-profile-page]')?.remove();
  mainArea.classList.add('profile-page-open');

  const cachedProfile = readProfileCache() || {
    fullName: window.Clerk?.user?.fullName || window.Clerk?.user?.firstName || '',
  };
  renderProfileImmediately(cachedProfile, currentSidebarAvatarUrl());
  window.requestAnimationFrame(refreshDomnAIProfileSilently);
}

function bindProfilePage() {
  const page = document.querySelector('[data-domnai-profile-page]');
  const form = page?.querySelector('.domnai-profile-form');
  if (!page || !form || form.dataset.bound === 'true') return;
  form.dataset.bound = 'true';

  page.querySelector('.domnai-profile-close')?.addEventListener('click', restoreDashboardFromProfile);
  page.querySelector('.domnai-profile-cancel')?.addEventListener('click', restoreDashboardFromProfile);
  page.querySelector('.domnai-profile-photo-input')?.addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const data = new FormData(); data.append('file', file, file.name);
    try {
      await profileFetch('/api/profile/avatar', { method: 'POST', body: data });
      window.dispatchEvent(new Event('domnai:profile-avatar-updated'));
      const avatarUrl = await profileAvatarUrl();
      const avatar = document.querySelector('[data-domnai-profile-page] .domnai-profile-avatar');
      if (avatar && avatarUrl) avatar.innerHTML = `<img src="${avatarUrl}" alt="Foto de perfil">`;
    } catch (error) { window.alert(error.message); }
  });
  page.querySelector('.domnai-profile-photo-remove')?.addEventListener('click', async () => {
    try {
      await profileFetch('/api/profile/avatar', { method: 'DELETE' });
      domnaiProfileAvatarMemory = '';
      window.dispatchEvent(new Event('domnai:profile-avatar-updated'));
      renderProfileImmediately(readProfileCache() || {}, '');
    } catch (error) { window.alert(error.message); }
  });
  form.elements.phone.addEventListener('input', () => { form.elements.phone.value = profileFormatPhone(form.elements.phone.value); });
  form.elements.cpf.addEventListener('input', () => { form.elements.cpf.value = profileFormatCpf(form.elements.cpf.value); });
  form.elements.zipCode.addEventListener('input', () => { form.elements.zipCode.value = profileFormatCep(form.elements.zipCode.value); });
  form.elements.state.addEventListener('input', (event) => { event.target.value = event.target.value.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 2); });
  ['birthDay','birthMonth','birthYear'].forEach((name) => form.elements[name].addEventListener('input', (event) => { event.target.value = event.target.value.replace(/\D/g, '').slice(0, Number(event.target.maxLength)); }));
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('.domnai-profile-save');
    const message = form.querySelector('.domnai-profile-message');
    const data = new FormData(form);
    const payload = {
      full_name: String(data.get('fullName')).trim(), phone: profileDigits(data.get('phone')), cpf: profileDigits(data.get('cpf')),
      birth_date: `${String(data.get('birthYear'))}-${String(data.get('birthMonth')).padStart(2,'0')}-${String(data.get('birthDay')).padStart(2,'0')}`,
      zip_code: profileDigits(data.get('zipCode')), street: String(data.get('street')).trim(), number: String(data.get('number')).trim(),
      complement: String(data.get('complement')).trim(), lot: String(data.get('lot')).trim(), block: String(data.get('block')).trim(), building: String(data.get('building')).trim(), apartment: String(data.get('apartment')).trim(),
      neighborhood: String(data.get('neighborhood')).trim(), city: String(data.get('city')).trim(), state: String(data.get('state')).trim().toUpperCase()
    };
    button.disabled = true; button.textContent = 'Salvando...'; message.hidden = true;
    try {
      await profileFetch('/api/profile', { method: 'PUT', body: JSON.stringify(payload) });
      writeProfileCache({
        fullName: payload.full_name, phone: payload.phone, cpf: payload.cpf, birthDate: payload.birth_date,
        zipCode: payload.zip_code, street: payload.street, number: payload.number, complement: payload.complement,
        lot: payload.lot, block: payload.block, building: payload.building, apartment: payload.apartment,
        neighborhood: payload.neighborhood, city: payload.city, state: payload.state,
      });
      message.textContent = 'Dados atualizados com sucesso.'; message.className = 'domnai-profile-message success'; message.hidden = false;
      button.disabled = false; button.textContent = 'Salvar alterações';
      window.dispatchEvent(new Event('domnai:profile-updated'));
    } catch (error) {
      message.textContent = error.message; message.className = 'domnai-profile-message error'; message.hidden = false; button.disabled = false; button.textContent = 'Salvar alterações';
    }
  });
}

function installNativeProfileTrigger() {
  const container = document.querySelector('.sidebar-profile');
  if (!container) return;
  if (!container.querySelector('.domnai-profile-trigger')) {
    container.innerHTML = `<button type="button" class="domnai-profile-trigger" aria-label="Abrir Minha conta"><span class="domnai-profile-trigger-avatar">${(window.Clerk?.user?.firstName || window.Clerk?.user?.primaryEmailAddress?.emailAddress || 'U').charAt(0).toUpperCase()}</span><span><strong>Minha conta</strong><small>Perfil e acesso</small></span></button>`;
  }
  container.dataset.domnaiProfileReady = 'true';
}

window.openDomnAIProfile = openDomnAIProfile;
window.addEventListener('click', (event) => {
  const trigger = event.target.closest('.domnai-profile-trigger, .sidebar-profile');
  if (!trigger) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  openDomnAIProfile();
}, true);

const profileObserver = new MutationObserver(installNativeProfileTrigger);
profileObserver.observe(document.documentElement, { childList: true, subtree: true });
installNativeProfileTrigger();
readProfileCache();
