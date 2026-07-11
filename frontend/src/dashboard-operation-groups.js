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
    ],
  },
];

function normalizedText(element) {
  return String(element?.textContent || '')
    .replace(/^›\s*/, '')
    .replace(/\s+/g, ' ')
    .trim();
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
  details.open = group.id === 'business';

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

const observer = new MutationObserver(organizeOperations);

function start() {
  organizeOperations();
  observer.observe(document.documentElement, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start, { once: true });
} else {
  start();
}
