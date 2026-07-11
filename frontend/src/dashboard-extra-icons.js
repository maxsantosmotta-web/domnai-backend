const extraMobileIcons = [
  {
    className: 'icon-6',
    label: 'Finanças',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="22"/><path d="M38 22h-9a6 6 0 0 0 0 12h6a6 6 0 0 1 0 12H25M32 16v32"/></svg>',
  },
  {
    className: 'icon-7',
    label: 'Trabalhista',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><rect x="10" y="20" width="44" height="30" rx="4"/><path d="M24 20v-5h16v5M10 31h44M27 31v5h10v-5"/></svg>',
  },
  {
    className: 'icon-8',
    label: 'Visão global',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="22"/><path d="M10 32h44M32 10c7 7 10 14 10 22s-3 15-10 22M32 10c-7 7-10 14-10 22s3 15 10 22"/></svg>',
  },
];

function appendExtraMobileIcons() {
  const layer = document.querySelector('.mobile-operation-icons');
  if (!layer) return;

  layer.querySelectorAll('.icon-6, .icon-7, .icon-8').forEach((icon) => icon.remove());

  extraMobileIcons.forEach((icon) => {
    const item = document.createElement('div');
    item.className = `mobile-operation-icon ${icon.className}`;
    item.title = icon.label;
    item.innerHTML = icon.svg;
    layer.appendChild(item);
  });
}

const extraIconsObserver = new MutationObserver(() => {
  const layer = document.querySelector('.mobile-operation-icons');
  if (!layer) return;

  const current = layer.querySelectorAll('.icon-6, .icon-7, .icon-8').length;
  if (current !== extraMobileIcons.length) appendExtraMobileIcons();
});

function startExtraIcons() {
  appendExtraMobileIcons();
  extraIconsObserver.observe(document.documentElement, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startExtraIcons, { once: true });
} else {
  startExtraIcons();
}
