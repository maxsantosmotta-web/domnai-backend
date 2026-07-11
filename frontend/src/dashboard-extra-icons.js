const extraMobileIcons = [
  {
    className: 'icon-6',
    label: 'Compras e patrimônio',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M12 18h6l5 25h25l5-18H21M27 51a3 3 0 1 0 0 .1M46 51a3 3 0 1 0 0 .1"/></svg>',
  },
  {
    className: 'icon-7',
    label: 'Viagens e mobilidade',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="22"/><path d="M10 32h44M32 10c7 7 10 14 10 22s-3 15-10 22M32 10c-7 7-10 14-10 22s3 15 10 22"/></svg>',
  },
];

function appendExtraMobileIcons() {
  const layer = document.querySelector('.mobile-operation-icons');
  if (!layer) return;

  extraMobileIcons.forEach((icon) => {
    if (layer.querySelector(`.${icon.className}`)) return;

    const item = document.createElement('div');
    item.className = `mobile-operation-icon ${icon.className}`;
    item.title = icon.label;
    item.innerHTML = icon.svg;
    layer.appendChild(item);
  });
}

const extraIconsObserver = new MutationObserver(appendExtraMobileIcons);

function startExtraIcons() {
  appendExtraMobileIcons();
  extraIconsObserver.observe(document.documentElement, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startExtraIcons, { once: true });
} else {
  startExtraIcons();
}
