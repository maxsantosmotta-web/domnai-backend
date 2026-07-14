const FEEDBACK_PAGE_SELECTOR = '[data-domnai-feedback-page="true"]';
const FEEDBACK_MENU_SELECTOR = '[data-domnai-feedback-menu="true"]';

const FEEDBACK_TYPES = {
  suggestion: { label: 'Sugestão', description: 'Uma ideia para melhorar o DomnAI.' },
  problem: { label: 'Problema', description: 'Algo não funcionou como deveria.' },
  praise: { label: 'Elogio', description: 'Conte o que funcionou bem para você.' },
};

function feedbackEscape(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function feedbackToken() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (window.Clerk?.session) return window.Clerk.session.getToken();
    await new Promise((resolve) => window.setTimeout(resolve, 75));
  }
  throw new Error('Sessão não encontrada. Entre novamente para continuar.');
}

async function feedbackFetch(url, options = {}) {
  const token = await feedbackToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item?.msg || 'Dado inválido').join(' · ')
      : typeof detail === 'string'
        ? detail
        : 'Não foi possível concluir a operação.';
    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

function feedbackDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function feedbackStars(rating, compact = false) {
  return `<span class="domnai-feedback-stars-readonly${compact ? ' compact' : ''}" aria-label="${rating} de 5 estrelas">${[1, 2, 3, 4, 5]
    .map((value) => `<span class="${value <= rating ? 'filled' : ''}">★</span>`)
    .join('')}</span>`;
}

function feedbackPageHtml() {
  return `
    <section class="internal-section domnai-feedback-page" data-domnai-feedback-page="true">
      <header class="domnai-feedback-header">
        <div>
          <span>Sua opinião</span>
          <h1>Feedback</h1>
          <p>Ajude o DomnAI a evoluir contando o que funcionou, o que pode melhorar ou o que apresentou problema.</p>
        </div>
        <button type="button" class="domnai-feedback-back">Voltar ao Dashboard</button>
      </header>

      <div class="domnai-feedback-layout">
        <form class="domnai-feedback-form">
          <div class="domnai-feedback-card-heading">
            <span>01</span>
            <div><h2>Conte sua experiência</h2><p>Seu feedback fica registrado e poderá ser acompanhado pela administração.</p></div>
          </div>

          <fieldset class="domnai-feedback-type-fieldset">
            <legend>Qual é o tipo do feedback?</legend>
            <div class="domnai-feedback-types">
              ${Object.entries(FEEDBACK_TYPES).map(([value, item]) => `
                <button type="button" data-feedback-category="${value}" aria-pressed="false">
                  <strong>${item.label}</strong>
                  <small>${item.description}</small>
                </button>
              `).join('')}
            </div>
          </fieldset>

          <fieldset class="domnai-feedback-rating-fieldset">
            <legend>Como você avalia sua experiência?</legend>
            <div class="domnai-feedback-rating" role="radiogroup" aria-label="Avaliação de 1 a 5 estrelas">
              ${[1, 2, 3, 4, 5].map((value) => `
                <button type="button" data-feedback-rating="${value}" role="radio" aria-checked="false" aria-label="${value} ${value === 1 ? 'estrela' : 'estrelas'}">★</button>
              `).join('')}
            </div>
            <p class="domnai-feedback-rating-caption">Selecione de 1 a 5 estrelas.</p>
          </fieldset>

          <label class="domnai-feedback-field">
            <span>Título</span>
            <input name="title" maxlength="120" minlength="3" required placeholder="Resuma seu feedback">
          </label>

          <label class="domnai-feedback-field">
            <span>Mensagem</span>
            <textarea name="message" maxlength="2000" minlength="10" required rows="7" placeholder="Explique com detalhes o que aconteceu ou o que gostaria de sugerir."></textarea>
            <small><span data-feedback-count="true">0</span>/2000 caracteres</small>
          </label>

          <p class="domnai-feedback-form-message" hidden></p>
          <button type="submit" class="domnai-feedback-submit">Enviar feedback</button>
        </form>

        <aside class="domnai-feedback-history-card">
          <div class="domnai-feedback-card-heading compact">
            <span>02</span>
            <div><h2>Seus feedbacks</h2><p>O histórico permanece disponível mesmo depois de sair da conta.</p></div>
          </div>
          <div class="domnai-feedback-history-list" aria-live="polite">
            <div class="domnai-feedback-loading"><span></span>Carregando histórico...</div>
          </div>
        </aside>
      </div>
    </section>
  `;
}

function feedbackHistoryHtml(items) {
  if (!items.length) {
    return `
      <div class="domnai-feedback-empty">
        <span>★</span>
        <strong>Nenhum feedback enviado</strong>
        <p>Quando você enviar sua primeira avaliação, ela aparecerá aqui.</p>
      </div>
    `;
  }

  return items.map((item) => {
    const category = FEEDBACK_TYPES[item.category]?.label || item.categoryLabel || 'Feedback';
    const safeMessage = feedbackEscape(item.message).replaceAll('\n', '<br>');
    return `
      <article class="domnai-feedback-history-item ${feedbackEscape(item.category)}">
        <div class="domnai-feedback-history-topline">
          <span class="domnai-feedback-category-badge">${feedbackEscape(category)}</span>
          <span class="domnai-feedback-status">${feedbackEscape(item.statusLabel || 'Recebido')}</span>
        </div>
        ${feedbackStars(Number(item.rating) || 0, true)}
        <h3>${feedbackEscape(item.title)}</h3>
        <p>${safeMessage}</p>
        <time datetime="${feedbackEscape(item.createdAt)}">${feedbackEscape(feedbackDate(item.createdAt))}</time>
      </article>
    `;
  }).join('');
}

async function loadFeedbackHistory(page) {
  const list = page?.querySelector('.domnai-feedback-history-list');
  if (!list) return;

  list.innerHTML = '<div class="domnai-feedback-loading"><span></span>Carregando histórico...</div>';
  try {
    const payload = await feedbackFetch('/api/feedback');
    if (!page.isConnected) return;
    list.innerHTML = feedbackHistoryHtml(payload?.items || []);
  } catch (error) {
    if (!page.isConnected) return;
    list.innerHTML = `<div class="domnai-feedback-history-error">${feedbackEscape(error.message)}</div>`;
  }
}

function setFeedbackCategory(page, category) {
  page.dataset.feedbackCategory = category;
  page.querySelectorAll('[data-feedback-category]').forEach((button) => {
    const selected = button.dataset.feedbackCategory === category;
    button.classList.toggle('is-selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
}

function setFeedbackRating(page, rating) {
  const normalized = Number(rating) || 0;
  page.dataset.feedbackRating = String(normalized);
  page.querySelectorAll('[data-feedback-rating]').forEach((button) => {
    const value = Number(button.dataset.feedbackRating);
    const filled = value <= normalized;
    button.classList.toggle('is-selected', filled);
    button.setAttribute('aria-checked', String(value === normalized));
  });

  const caption = page.querySelector('.domnai-feedback-rating-caption');
  if (caption) {
    caption.textContent = normalized
      ? `${normalized} de 5 ${normalized === 1 ? 'estrela selecionada' : 'estrelas selecionadas'}.`
      : 'Selecione de 1 a 5 estrelas.';
  }
}

function closeFeedbackPage() {
  document.querySelector(FEEDBACK_PAGE_SELECTOR)?.remove();
  document.querySelector('.domnai-main-area')?.classList.remove('feedback-page-open');
  document.querySelector(FEEDBACK_MENU_SELECTOR)?.classList.remove('is-active');
}

function bindFeedbackPage(page) {
  if (!page || page.dataset.bound === 'true') return;
  page.dataset.bound = 'true';

  const form = page.querySelector('.domnai-feedback-form');
  const messageInput = form?.elements.message;
  const count = page.querySelector('[data-feedback-count]');
  const formMessage = page.querySelector('.domnai-feedback-form-message');
  const submit = page.querySelector('.domnai-feedback-submit');

  page.querySelector('.domnai-feedback-back')?.addEventListener('click', closeFeedbackPage);

  page.querySelectorAll('[data-feedback-category]').forEach((button) => {
    button.addEventListener('click', () => setFeedbackCategory(page, button.dataset.feedbackCategory));
  });

  page.querySelectorAll('[data-feedback-rating]').forEach((button) => {
    button.addEventListener('click', () => setFeedbackRating(page, Number(button.dataset.feedbackRating)));
  });

  messageInput?.addEventListener('input', () => {
    if (count) count.textContent = String(messageInput.value.length);
  });

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const category = page.dataset.feedbackCategory || '';
    const rating = Number(page.dataset.feedbackRating || 0);
    const title = String(form.elements.title.value || '').trim();
    const message = String(form.elements.message.value || '').trim();

    const showMessage = (text, type = 'error') => {
      formMessage.hidden = false;
      formMessage.className = `domnai-feedback-form-message ${type}`;
      formMessage.textContent = text;
    };

    if (!category) return showMessage('Selecione se o feedback é uma sugestão, problema ou elogio.');
    if (rating < 1 || rating > 5) return showMessage('Selecione uma avaliação de 1 a 5 estrelas.');
    if (title.length < 3) return showMessage('Informe um título com pelo menos 3 caracteres.');
    if (message.length < 10) return showMessage('Descreva seu feedback com pelo menos 10 caracteres.');

    submit.disabled = true;
    submit.textContent = 'Enviando...';
    formMessage.hidden = true;

    try {
      await feedbackFetch('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({ category, rating, title, message }),
      });
      form.reset();
      setFeedbackCategory(page, '');
      setFeedbackRating(page, 0);
      if (count) count.textContent = '0';
      showMessage('Feedback enviado com sucesso. Obrigado por ajudar o DomnAI a evoluir.', 'success');
      await loadFeedbackHistory(page);
    } catch (error) {
      showMessage(error.message || 'Não foi possível enviar o feedback.');
    } finally {
      submit.disabled = false;
      submit.textContent = 'Enviar feedback';
    }
  });

  loadFeedbackHistory(page);
}

function openFeedbackPage() {
  const mainArea = document.querySelector('.domnai-main-area');
  if (!mainArea) return;

  document.querySelector('[data-domnai-profile-page]')?.remove();
  mainArea.classList.remove('profile-page-open');
  closeFeedbackPage();
  mainArea.classList.add('feedback-page-open');
  mainArea.insertAdjacentHTML('beforeend', feedbackPageHtml());

  const menuButton = document.querySelector(FEEDBACK_MENU_SELECTOR);
  menuButton?.classList.add('is-active');

  const sidebar = document.querySelector('.domnai-sidebar');
  const closeButton = sidebar?.querySelector('.sidebar-close');
  if (sidebar?.classList.contains('is-open') && closeButton) closeButton.click();
  else sidebar?.classList.remove('is-open');

  bindFeedbackPage(mainArea.querySelector(FEEDBACK_PAGE_SELECTOR));
}

function installFeedbackMenu() {
  const group = document.querySelector('.sidebar-system-group');
  if (!group || group.querySelector(FEEDBACK_MENU_SELECTOR)) return;

  const button = document.createElement('button');
  button.type = 'button';
  button.dataset.domnaiFeedbackMenu = 'true';
  button.className = 'domnai-feedback-menu-button';
  button.innerHTML = '<span>★</span> Feedback';
  button.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    openFeedbackPage();
  });

  const billingButton = [...group.querySelectorAll(':scope > button')]
    .find((item) => String(item.textContent || '').trim().includes('Faturamento'));
  if (billingButton?.nextSibling) group.insertBefore(button, billingButton.nextSibling);
  else group.appendChild(button);
}

window.addEventListener('click', (event) => {
  const sidebarButton = event.target.closest('.sidebar-navigation button');
  if (!sidebarButton || sidebarButton.matches(FEEDBACK_MENU_SELECTOR)) return;
  closeFeedbackPage();
}, true);

const feedbackMenuObserver = new MutationObserver(() => {
  window.requestAnimationFrame(installFeedbackMenu);
});
feedbackMenuObserver.observe(document.documentElement, { childList: true, subtree: true });
installFeedbackMenu();
