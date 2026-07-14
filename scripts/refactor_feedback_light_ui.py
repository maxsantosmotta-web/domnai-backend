from pathlib import Path
import re

FEEDBACK = Path('/frontend/src/dashboard-feedback.js')
MAIN = Path('/frontend/src/main.jsx')


def replace_function(source: str, start: str, end: str, replacement: str, label: str) -> str:
    pattern = re.compile(re.escape(start) + r'.*?(?=' + re.escape(end) + r')', re.S)
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise SystemExit(f'{label}: esperado 1 bloco, encontrado {len(matches)}.')
    match = matches[0]
    return source[:match.start()] + replacement + '\n\n' + source[match.end():]


source = FEEDBACK.read_text(encoding='utf-8')

page_html = r'''function feedbackPageHtml() {
  return `
    <section class="internal-section domnai-feedback-page" data-domnai-feedback-page="true">
      <header class="domnai-feedback-header">
        <h1>Feedback</h1>
        <button type="button" class="domnai-feedback-back">Voltar</button>
      </header>

      <form class="domnai-feedback-form">
        <div class="domnai-feedback-intro">
          <h2>Como foi sua experiência?</h2>
        </div>

        <fieldset class="domnai-feedback-rating-fieldset">
          <div class="domnai-feedback-rating" role="radiogroup" aria-label="Avaliação de 1 a 5 estrelas">
            ${[1, 2, 3, 4, 5].map((value) => `
              <button type="button" data-feedback-rating="${value}" role="radio" aria-checked="false" aria-label="${value} ${value === 1 ? 'estrela' : 'estrelas'}">★</button>
            `).join('')}
          </div>
          <p class="domnai-feedback-rating-caption">Selecione de 1 a 5 estrelas.</p>
        </fieldset>

        <fieldset class="domnai-feedback-type-fieldset">
          <div class="domnai-feedback-types">
            ${Object.entries(FEEDBACK_TYPES).map(([value, item]) => `
              <button type="button" data-feedback-category="${value}" aria-pressed="false">${item.label}</button>
            `).join('')}
          </div>
        </fieldset>

        <div class="domnai-feedback-suggestion-options" data-feedback-suggestion-options="true" hidden>
          <button type="button" data-feedback-suggestion="improvements" aria-pressed="false">Sugestão de melhorias</button>
          <button type="button" data-feedback-suggestion="operation" aria-pressed="false">Sugestão de operação</button>
        </div>

        <label class="domnai-feedback-field">
          <span>Conte para nós</span>
          <textarea name="message" maxlength="2000" minlength="10" required rows="5" placeholder="Escreva sua experiência, ideia ou problema."></textarea>
        </label>

        <p class="domnai-feedback-form-message" hidden></p>
        <button type="submit" class="domnai-feedback-submit">Enviar feedback</button>
      </form>

      <button type="button" class="domnai-feedback-history-toggle" aria-expanded="false">Meus feedbacks</button>
      <section class="domnai-feedback-history-card" hidden>
        <div class="domnai-feedback-history-list" aria-live="polite"></div>
      </section>
    </section>
  `;
}'''
source = replace_function(source, 'function feedbackPageHtml() {', 'function feedbackHistoryHtml(items) {', page_html, 'HTML da página de feedback')

category_functions = r'''function setFeedbackCategory(page, category) {
  page.dataset.feedbackCategory = category;
  page.querySelectorAll('[data-feedback-category]').forEach((button) => {
    const selected = button.dataset.feedbackCategory === category;
    button.classList.toggle('is-selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });

  const suggestionOptions = page.querySelector('[data-feedback-suggestion-options]');
  if (suggestionOptions) suggestionOptions.hidden = category !== 'suggestion';
  if (category !== 'suggestion') setFeedbackSuggestion(page, '');
}

function setFeedbackSuggestion(page, suggestion) {
  page.dataset.feedbackSuggestion = suggestion;
  page.querySelectorAll('[data-feedback-suggestion]').forEach((button) => {
    const selected = button.dataset.feedbackSuggestion === suggestion;
    button.classList.toggle('is-selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
}

function feedbackGeneratedTitle(category, suggestion) {
  if (category === 'suggestion') {
    return suggestion === 'operation' ? 'Sugestão de operação' : 'Sugestão de melhorias';
  }
  if (category === 'problem') return 'Problema relatado';
  return 'Elogio';
}

async function toggleFeedbackHistory(page) {
  const card = page?.querySelector('.domnai-feedback-history-card');
  const toggle = page?.querySelector('.domnai-feedback-history-toggle');
  if (!card || !toggle) return;

  const opening = card.hidden;
  card.hidden = !opening;
  toggle.setAttribute('aria-expanded', String(opening));
  toggle.textContent = opening ? 'Ocultar feedbacks' : 'Meus feedbacks';

  if (opening && page.dataset.feedbackHistoryLoaded !== 'true') {
    await loadFeedbackHistory(page);
    page.dataset.feedbackHistoryLoaded = 'true';
  }
}'''
source = replace_function(source, 'function setFeedbackCategory(page, category) {', 'function setFeedbackRating(page, rating) {', category_functions, 'Estado das categorias do feedback')

bind_function = r'''function bindFeedbackPage(page) {
  if (!page || page.dataset.bound === 'true') return;
  page.dataset.bound = 'true';

  const form = page.querySelector('.domnai-feedback-form');
  const formMessage = page.querySelector('.domnai-feedback-form-message');
  const submit = page.querySelector('.domnai-feedback-submit');

  page.querySelector('.domnai-feedback-back')?.addEventListener('click', closeFeedbackPage);
  page.querySelector('.domnai-feedback-history-toggle')?.addEventListener('click', () => toggleFeedbackHistory(page));

  page.querySelectorAll('[data-feedback-category]').forEach((button) => {
    button.addEventListener('click', () => setFeedbackCategory(page, button.dataset.feedbackCategory));
  });

  page.querySelectorAll('[data-feedback-suggestion]').forEach((button) => {
    button.addEventListener('click', () => setFeedbackSuggestion(page, button.dataset.feedbackSuggestion));
  });

  page.querySelectorAll('[data-feedback-rating]').forEach((button) => {
    button.addEventListener('click', () => setFeedbackRating(page, Number(button.dataset.feedbackRating)));
  });

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const category = page.dataset.feedbackCategory || '';
    const suggestion = page.dataset.feedbackSuggestion || '';
    const rating = Number(page.dataset.feedbackRating || 0);
    const message = String(form.elements.message.value || '').trim();
    const title = feedbackGeneratedTitle(category, suggestion);

    const showMessage = (text, type = 'error') => {
      formMessage.hidden = false;
      formMessage.className = `domnai-feedback-form-message ${type}`;
      formMessage.textContent = text;
    };

    if (!category) return showMessage('Escolha Sugestão, Problema ou Elogio.');
    if (category === 'suggestion' && !suggestion) return showMessage('Escolha Sugestão de melhorias ou Sugestão de operação.');
    if (rating < 1 || rating > 5) return showMessage('Selecione uma avaliação de 1 a 5 estrelas.');
    if (message.length < 10) return showMessage('Conte sua experiência com pelo menos 10 caracteres.');

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
      setFeedbackSuggestion(page, '');
      setFeedbackRating(page, 0);
      showMessage('Feedback enviado. Obrigado!', 'success');

      if (!page.querySelector('.domnai-feedback-history-card')?.hidden) {
        await loadFeedbackHistory(page);
        page.dataset.feedbackHistoryLoaded = 'true';
      } else {
        page.dataset.feedbackHistoryLoaded = 'false';
      }
    } catch (error) {
      showMessage(error.message || 'Não foi possível enviar o feedback.');
    } finally {
      submit.disabled = false;
      submit.textContent = 'Enviar feedback';
    }
  });
}'''
source = replace_function(source, 'function bindFeedbackPage(page) {', 'function openFeedbackPage() {', bind_function, 'Eventos da página de feedback')

FEEDBACK.write_text(source, encoding='utf-8')

main_source = MAIN.read_text(encoding='utf-8')
old_import = "import './dashboard-feedback.css';\n"
new_import = "import './dashboard-feedback.css';\nimport './dashboard-feedback-light.css';\n"
if main_source.count(old_import) != 1:
    raise SystemExit('Importação original do feedback não encontrada exatamente uma vez.')
MAIN.write_text(main_source.replace(old_import, new_import, 1), encoding='utf-8')

print('Feedback simplificado com títulos automáticos e histórico recolhido.')
