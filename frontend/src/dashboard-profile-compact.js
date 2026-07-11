function compactProfileFields() {
  const page = document.querySelector('[data-domnai-profile-page]');
  const form = page?.querySelector('.domnai-profile-form');
  if (!page || !form || form.dataset.compactReady === 'true') return;

  form.dataset.compactReady = 'true';

  form.querySelectorAll('.domnai-profile-grid > label').forEach((label) => {
    const input = label.querySelector('input');
    if (!input) return;

    const optional = Boolean(label.querySelector('small'));
    const rawText = [...label.childNodes]
      .filter((node) => node.nodeType === Node.TEXT_NODE)
      .map((node) => node.textContent.trim())
      .filter(Boolean)
      .join(' ');

    label.classList.add('domnai-compact-field');
    if (optional) label.classList.add('is-optional');

    [...label.childNodes].forEach((node) => {
      if (node !== input) node.remove();
    });

    const caption = document.createElement('span');
    caption.className = 'domnai-compact-label';
    caption.textContent = optional ? `${rawText} · opcional` : rawText;
    label.insertBefore(caption, input);
  });

  const birthField = form.querySelector('.domnai-birth-field');
  if (birthField) {
    birthField.classList.add('domnai-compact-birth');
    const title = birthField.querySelector(':scope > span');
    if (title) title.textContent = 'Data de nascimento';
    birthField.querySelectorAll('label').forEach((label) => {
      const input = label.querySelector('input');
      if (!input) return;
      const name = [...label.childNodes]
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent.trim())
        .filter(Boolean)
        .join(' ');
      [...label.childNodes].forEach((node) => {
        if (node !== input) node.remove();
      });
      const caption = document.createElement('span');
      caption.className = 'domnai-compact-label';
      caption.textContent = name;
      label.insertBefore(caption, input);
      label.classList.add('domnai-compact-field');
    });
  }

  const addressCard = [...form.querySelectorAll('.domnai-profile-card')]
    .find((card) => card.querySelector('h2')?.textContent.trim() === 'Endereço completo');
  const addressGrid = addressCard?.querySelector('.domnai-profile-grid');
  if (addressGrid && !addressCard.querySelector('.domnai-address-details')) {
    const optionalNames = ['complement', 'lot', 'block', 'building', 'apartment'];
    const optionalLabels = optionalNames
      .map((name) => addressGrid.querySelector(`input[name="${name}"]`)?.closest('label'))
      .filter(Boolean);

    if (optionalLabels.length) {
      const details = document.createElement('details');
      details.className = 'domnai-address-details';
      details.innerHTML = '<summary>Mais detalhes do endereço <span>opcional</span></summary><div class="domnai-address-details-grid"></div>';
      const detailsGrid = details.querySelector('.domnai-address-details-grid');
      optionalLabels.forEach((label) => detailsGrid.appendChild(label));
      addressCard.appendChild(details);
    }
  }
}

const compactProfileObserver = new MutationObserver(() => compactProfileFields());
compactProfileObserver.observe(document.documentElement, { childList: true, subtree: true });
compactProfileFields();
