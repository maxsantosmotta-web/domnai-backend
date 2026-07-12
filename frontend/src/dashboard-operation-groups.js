const operationGroups = [
  {
    id: 'business',
    title: 'Negócios e Finanças',
    operations: [
      'Validação de Ideias e Oportunidades',
      'Abrir um Negócio do Zero',
      'Estruturação e Organização Empresarial',
      'Diagnóstico do Negócio',
      'Plano de Ação Empresarial',
      'Análise de Viabilidade',
      'Pesquisa de Mercado e Concorrência',
      'Gestão Financeira Empresarial',
      'Precificação Estratégica',
      'Planejamento de Metas',
      'Cotações e Compras Empresariais',
      'Escolha de Fornecedores',
      'Negociação Estratégica',
      'Análise de Dívidas e Renegociação',
      'Análise de Investimentos',
      'Análise Contratual',
      'Cálculo de Rescisão Trabalhista',
    ],
  },
  {
    id: 'assets',
    title: 'Compras e Patrimônio',
    operations: [
      'Pesquisa e Comparação de Veículos',
      'Análise Imobiliária',
      'Análise de Compras Pessoais de Alto Valor',
      'Planejamento de Viagens e Orçamento',
    ],
  },
  {
    id: 'career',
    title: 'Carreira e Desenvolvimento',
    operations: [
      'Análise de Tendências Profissionais e Carreiras',
      'Planejamento de Estudos e Qualificação Profissional',
      'Organização Financeira Pessoal',
    ],
  },
  {
    id: 'fitness',
    title: 'Saúde, Fitness e Esportes',
    operations: [
      'Planejamento de Treinos para Academia',
      'Planejamento de Exercícios em Casa',
      'Análise de Alimentação e Rotina Fitness',
      'Análise Estatística Esportiva para Apostas',
      'Pilates para Fazer em Casa',
      'Yoga para Fazer em Casa',
      'Cronograma Capilar Personalizado',
      'Cuidados com a Pele em Casa',
      'Plano de Treino Esportivo',
      'Preparação para Corrida',
      'Plano de Alongamento e Mobilidade',
      'Preparação Física para Esportes',
    ],
  },
];

const mobileEmptyIcons = [
  {
    label: 'Decisões e contratos',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M32 10v42M18 16h28M12 22l-7 13h14L12 22Zm40 0-7 13h14L52 22ZM19 52h26"/></svg>',
  },
  {
    label: 'Mercado e crescimento',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M10 50V14M10 50h44M17 42l10-11 9 7 15-19M43 19h8v8"/></svg>',
  },
  {
    label: 'Planejamento e análise',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M18 8h22l8 8v40H18V8Zm22 0v10h10M25 29h16M25 38h16M25 47h11"/></svg>',
  },
  {
    label: 'Saúde e fitness',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M8 26v12M14 22v20M20 28h24M44 22v20M50 26v12"/></svg>',
  },
  {
    label: 'Carreira e escolhas',
    svg: '<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="23"/><path d="m39 22-5 13-13 6 6-14 12-5Z"/></svg>',
  },
];

function normalizedText(element) {
  return String(element?.textContent || '')
    .replace(/^›\s*/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function closeAllOperationGroups() {
  document.querySelectorAll('.operation-category[open]').forEach((group) => {
    group.removeAttribute('open');
  });
}

function setReactTextareaValue(textarea, value) {
  const descriptor = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype,
    'value',
  );
  descriptor?.set?.call(textarea, value);
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
}

function sendNewOperation(title) {
  const textarea = document.querySelector('.chat-composer textarea');
  const form = document.querySelector('.chat-composer');

  if (!textarea || !form) {
    const dashboardButton = [...document.querySelectorAll('.sidebar-navigation > button')]
      .find((button) => normalizedText(button) === '▣ Dashboard' || normalizedText(button) === 'Dashboard');
    dashboardButton?.click();
    window.setTimeout(() => sendNewOperation(title), 80);
    return;
  }

  setReactTextareaValue(textarea, title);
  window.setTimeout(() => form.requestSubmit(), 0);

  closeAllOperationGroups();
  const sidebar = document.querySelector('.domnai-sidebar');
  sidebar?.classList.remove('is-open');
  document.querySelector('.sidebar-backdrop')?.click();
}

function createNewOperationButton(title) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'grouped-operation-button';
  button.innerHTML = `<span>›</span> ${title}`;
  button.addEventListener('click', () => sendNewOperation(title));
  return button;
}

function createGroup(group, existingButtons) {
  const details = document.createElement('details');
  details.className = 'operation-category';
  details.dataset.operationGroup = group.id;

  const summary = document.createElement('summary');
  summary.innerHTML = `<span>${group.title}</span><small>${group.operations.length}</small>`;
  details.appendChild(summary);

  const body = document.createElement('div');
  body.className = 'operation-category-body';

  group.operations.forEach((title) => {
    const existing = existingButtons.get(title);
    body.appendChild(existing || createNewOperationButton(title));
  });

  details.appendChild(body);
  return details;
}

function organizeOperations() {
  const container = document.querySelector('.operations-only');
  if (!container || container.dataset.grouped === 'true') return;

  const buttons = [...container.querySelectorAll(':scope > button')];
  if (!buttons.length) return;

  const existingButtons = new Map(
    buttons.map((button) => [normalizedText(button), button]),
  );

  const heading = container.querySelector(':scope > p');
  container.innerHTML = '';
  if (heading) {
    heading.textContent = 'Operações';
    container.appendChild(heading);
  }

  operationGroups.forEach((group) => {
    container.appendChild(createGroup(group, existingButtons));
  });

  container.dataset.grouped = 'true';
}

function createMobileEmptyState() {
  const workspace = document.querySelector('.chat-workspace');
  if (!workspace || workspace.querySelector('.mobile-operation-icons')) return;

  const layer = document.createElement('div');
  layer.className = 'mobile-operation-icons';
  layer.setAttribute('aria-hidden', 'true');

  mobileEmptyIcons.forEach((icon, index) => {
    const item = document.createElement('div');
    item.className = `mobile-operation-icon icon-${index + 1}`;
    item.title = icon.label;
    item.innerHTML = icon.svg;
    layer.appendChild(item);
  });

  workspace.appendChild(layer);
}

function updateMobileEmptyState() {
  createMobileEmptyState();

  const layer = document.querySelector('.mobile-operation-icons');
  if (!layer) return;

  const sidebarOpen = document.querySelector('.domnai-sidebar')?.classList.contains('is-open');
  const hasMessages = Boolean(document.querySelector('.chat-messages .chat-message'));
  const hasPendingAttachments = Boolean(document.querySelector('.attachment-preview')?.children.length);
  const isChatVisible = Boolean(document.querySelector('.chat-workspace'));

  layer.classList.toggle(
    'is-visible',
    Boolean(isChatVisible && !sidebarOpen && !hasMessages && !hasPendingAttachments),
  );
}

function bindSidebarReset() {
  if (document.documentElement.dataset.operationSidebarBound === 'true') return;
  document.documentElement.dataset.operationSidebarBound = 'true';

  document.addEventListener('click', (event) => {
    const openButton = event.target.closest('.mobile-menu-button');
    const closeButton = event.target.closest('.sidebar-close, .sidebar-backdrop');

    if (openButton || closeButton) {
      closeAllOperationGroups();
      window.setTimeout(updateMobileEmptyState, 20);
    }
  }, true);
}

const observer = new MutationObserver(() => {
  organizeOperations();
  updateMobileEmptyState();
});

function start() {
  organizeOperations();
  bindSidebarReset();
  updateMobileEmptyState();
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class'],
  });
  window.addEventListener('resize', updateMobileEmptyState);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start, { once: true });
} else {
  start();
}
