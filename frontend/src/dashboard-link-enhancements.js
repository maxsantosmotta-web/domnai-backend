function isHttpUrl(value) {
  return /^https?:\/\//i.test(String(value || '').trim());
}

function copyLink(value, button) {
  const text = String(value || '').trim();
  if (!text) return;

  const done = () => {
    const original = button.textContent;
    button.textContent = 'Copiado';
    window.setTimeout(() => {
      button.textContent = original;
    }, 1400);
  };

  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => {});
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  textarea.remove();
  done();
}

function enhanceLinkCard(card) {
  if (!(card instanceof HTMLElement) || card.dataset.linkEnhanced === 'true') return;

  const strong = card.querySelector('.native-file-copy strong');
  const url = strong?.textContent?.trim();
  if (!isHttpUrl(url)) return;

  card.dataset.linkEnhanced = 'true';
  card.classList.add('is-real-link');

  const badge = card.querySelector('.native-file-badge');
  const size = card.querySelector('.native-file-copy small');
  const action = card.querySelector('.native-file-action');

  if (badge) badge.textContent = 'LINK';
  if (size) size.remove();
  if (action) action.textContent = 'Abrir link';

  card.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    window.open(url, '_blank', 'noopener,noreferrer');
  }, true);

  const wrapper = card.closest('.chat-native-file, .composer-native-file');
  if (!wrapper || wrapper.querySelector('.copy-link-button')) return;

  const copyButton = document.createElement('button');
  copyButton.type = 'button';
  copyButton.className = 'copy-link-button';
  copyButton.textContent = 'Copiar link';
  copyButton.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    copyLink(url, copyButton);
  });

  const deleteButton = wrapper.querySelector('.native-delete-button, :scope > button:last-child');
  if (deleteButton) wrapper.insertBefore(copyButton, deleteButton);
  else wrapper.appendChild(copyButton);
}

function enhanceDashboard() {
  document.querySelectorAll('.message-author').forEach((element) => element.remove());
  document.querySelectorAll('.native-file-card.link, .native-file-card.file').forEach(enhanceLinkCard);
}

const observer = new MutationObserver(enhanceDashboard);

function start() {
  enhanceDashboard();
  observer.observe(document.documentElement, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start, { once: true });
} else {
  start();
}
