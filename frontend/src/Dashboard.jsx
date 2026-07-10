import React, { useMemo, useState } from 'react';
import { UserButton } from '@clerk/clerk-react';
import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';
import './dashboard.css';

const operations = [
  { id: 'validacao-ideia', name: 'Validação de Ideias e Oportunidades', prompt: 'Informe a ideia, produto, serviço ou oportunidade para analisar demanda, público, concorrência, custos, riscos e potencial de retorno.', numeric: true },
  { id: 'abrir-negocio', name: 'Abrir um Negócio do Zero', prompt: 'Conte qual negócio pretende abrir, quanto pretende investir, onde deseja atuar e se será físico, digital ou híbrido.', numeric: true },
  { id: 'estrutura-negocio', name: 'Estruturação e Organização Empresarial', prompt: 'Conte como o negócio funciona para organizar modelo, processos, setores, responsabilidades, custos e próximos passos.', numeric: false },
  { id: 'diagnostico-negocio', name: 'Diagnóstico do Negócio', prompt: 'Informe como sua empresa funciona hoje para identificar gargalos em vendas, custos, operação, equipe, margem e organização.', numeric: true },
  { id: 'plano-acao', name: 'Plano de Ação Empresarial', prompt: 'Explique o problema ou objetivo para transformar a situação em ações organizadas por prioridade, prazo e impacto.', numeric: false },
  { id: 'viabilidade', name: 'Análise de Viabilidade', prompt: 'Informe a decisão que está avaliando para analisar custos, riscos, retorno, prazo e alternativas antes de investir.', numeric: true },
  { id: 'mercado-concorrencia', name: 'Pesquisa de Mercado e Concorrência', prompt: 'Informe o mercado, produto, serviço ou região para organizar concorrentes, preços, público, diferenciais e oportunidades.', numeric: true },
  { id: 'gestao-financeira', name: 'Gestão Financeira Empresarial', prompt: 'Informe receitas, despesas, custos e período para organizar fluxo de caixa, margem e resultado.', numeric: true },
  { id: 'precificacao', name: 'Precificação Estratégica', prompt: 'Informe custo, taxas, impostos, margem e demais despesas para calcular preço mínimo, ideal e promocional.', numeric: true },
  { id: 'metas', name: 'Planejamento de Metas', prompt: 'Informe a meta de faturamento, lucro ou crescimento para calcular vendas necessárias, ticket médio, prazo e prioridades.', numeric: true },
  { id: 'compras', name: 'Cotações e Compras Empresariais', prompt: 'Envie produtos, fornecedores ou orçamentos para comparar preço, frete, prazo, desconto e custo total.', numeric: true },
  { id: 'fornecedores', name: 'Escolha de Fornecedores', prompt: 'Envie as opções de fornecedores para comparar preço, prazo, qualidade, reputação, frete e condições de pagamento.', numeric: true },
  { id: 'negociacao', name: 'Negociação Estratégica', prompt: 'Explique o que precisa negociar e informe valores, condições e objetivo desejado.', numeric: false },
  { id: 'dividas', name: 'Análise de Dívidas e Renegociação', prompt: 'Informe saldo, juros, parcelas e propostas de acordo para comparar cenários e identificar a opção menos pesada para o caixa.', numeric: true },
  { id: 'investimentos', name: 'Análise de Investimentos', prompt: 'Informe valor, prazo, rentabilidade esperada e alternativas para comparar risco, liquidez e retorno.', numeric: true },
  { id: 'contrato', name: 'Análise Contratual', prompt: 'Envie o contrato em PDF, imagem ou texto para identificar riscos, multas, prazos e obrigações.', numeric: false },
  { id: 'rescisao', name: 'Cálculo de Rescisão Trabalhista', prompt: 'Informe salário, datas, tipo de desligamento, férias e demais dados para estimar as verbas rescisórias.', numeric: true },
  { id: 'veiculos', name: 'Pesquisa e Comparação de Veículos', prompt: 'Informe placa, modelo, ano ou os veículos que deseja comparar por FIPE, mercado, consumo, manutenção e custo-benefício.', numeric: true },
  { id: 'imoveis', name: 'Análise Imobiliária', prompt: 'Envie os dados do imóvel para comparar preço, localização, documentação, financiamento e retorno.', numeric: true },
];

const initialMessages = [
  {
    id: 1,
    role: 'assistant',
    text: 'Olá. Escolha uma operação no menu ou escreva diretamente o que você precisa analisar.',
  },
];

export default function Dashboard() {
  const [section, setSection] = useState('chat');
  const [activeOperation, setActiveOperation] = useState(null);
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState('');
  const [search, setSearch] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [trash, setTrash] = useState([]);

  const operation = useMemo(
    () => operations.find((item) => item.id === activeOperation) || null,
    [activeOperation],
  );

  const visibleMessages = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return messages;
    return messages.filter((message) => message.text.toLowerCase().includes(term));
  }, [messages, search]);

  function selectOperation(item) {
    setActiveOperation(item.id);
    setSection('chat');
    setSidebarOpen(false);
    setMessages((current) => [
      ...current,
      {
        id: Date.now(),
        role: 'assistant',
        text: `${item.name}: ${item.prompt}`,
      },
    ]);
  }

  function sendMessage(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;

    setMessages((current) => [
      ...current,
      { id: Date.now(), role: 'user', text },
      {
        id: Date.now() + 1,
        role: 'assistant',
        text: operation
          ? `Recebi os dados para ${operation.name}. A próxima etapa será conectar esta conversa à análise real da operação.`
          : 'Recebi sua mensagem. Selecione uma operação no menu para aplicar a análise especializada.',
      },
    ]);
    setDraft('');
  }

  function deleteConversation() {
    if (messages.length === 0) return;
    setTrash((current) => [
      { id: Date.now(), title: operation?.name || 'Conversa geral', messages, deletedAt: new Date().toLocaleString('pt-BR') },
      ...current,
    ]);
    setMessages(initialMessages);
    setActiveOperation(null);
    setSearch('');
  }

  function restoreConversation(item) {
    setMessages(item.messages);
    setTrash((current) => current.filter((entry) => entry.id !== item.id));
    setSection('chat');
  }

  function emptyTrash() {
    setTrash([]);
  }

  return (
    <main className="domnai-app-shell">
      <button
        type="button"
        className="mobile-menu-button"
        aria-label="Abrir menu"
        onClick={() => setSidebarOpen(true)}
      >
        ☰
      </button>

      {sidebarOpen ? <button className="sidebar-backdrop" type="button" aria-label="Fechar menu" onClick={() => setSidebarOpen(false)} /> : null}

      <aside className={`domnai-sidebar${sidebarOpen ? ' is-open' : ''}`}>
        <div className="sidebar-brand">
          <img src={DOMNAI_LOGO} alt="DomnAI" />
          <button type="button" className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu">×</button>
        </div>

        <nav className="sidebar-navigation" aria-label="Navegação principal">
          <button className={section === 'chat' ? 'is-active' : ''} type="button" onClick={() => { setSection('chat'); setSidebarOpen(false); }}>
            <span>▣</span> Dashboard
          </button>

          <div className="sidebar-group">
            <p>Operações</p>
            {operations.map((item) => (
              <button
                className={activeOperation === item.id && section === 'chat' ? 'is-active' : ''}
                type="button"
                key={item.id}
                onClick={() => selectOperation(item)}
              >
                <span>›</span> {item.name}
              </button>
            ))}
          </div>

          <div className="sidebar-group sidebar-system-group">
            <p>Sistema</p>
            <button className={section === 'trash' ? 'is-active' : ''} type="button" onClick={() => { setSection('trash'); setSidebarOpen(false); }}>
              <span>⌫</span> Lixeira
            </button>
            <button className={section === 'billing' ? 'is-active' : ''} type="button" onClick={() => { setSection('billing'); setSidebarOpen(false); }}>
              <span>◈</span> Faturamento
            </button>
            <button className={section === 'settings' ? 'is-active' : ''} type="button" onClick={() => { setSection('settings'); setSidebarOpen(false); }}>
              <span>⚙</span> Configurações
            </button>
          </div>
        </nav>

        <div className="sidebar-profile">
          <UserButton afterSignOutUrl="/" />
          <div>
            <strong>Minha conta</strong>
            <small>Perfil e acesso</small>
          </div>
        </div>
      </aside>

      <section className="domnai-main-area">
        {section === 'chat' ? (
          <>
            <header className="chat-header">
              <div>
                <span className="chat-kicker">{operation ? 'Operação ativa' : 'DomnAI'}</span>
                <h1>{operation?.name || 'Dashboard'}</h1>
                <p>{operation?.prompt || 'Continue de onde parou ou escolha uma operação no menu lateral.'}</p>
              </div>

              <div className="chat-header-actions">
                <label className="chat-search">
                  <span aria-hidden="true">⌕</span>
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Pesquisar na conversa"
                    aria-label="Pesquisar por palavra-chave"
                  />
                </label>
                <button type="button" className="delete-chat-button" onClick={deleteConversation}>Excluir conversa</button>
              </div>
            </header>

            <div className={`chat-workspace${operation?.numeric ? ' has-dynamic-panel' : ''}`}>
              <section className="chat-column">
                <div className="chat-messages">
                  {visibleMessages.length ? visibleMessages.map((message) => (
                    <article className={`chat-message ${message.role}`} key={message.id}>
                      <span>{message.role === 'assistant' ? 'DomnAI' : 'Você'}</span>
                      <p>{message.text}</p>
                      {message.role === 'assistant' ? (
                        <button type="button" onClick={() => navigator.clipboard?.writeText(message.text)}>Copiar</button>
                      ) : null}
                    </article>
                  )) : (
                    <div className="chat-empty-search">Nenhuma mensagem encontrada com essa palavra.</div>
                  )}
                </div>

                <form className="chat-composer" onSubmit={sendMessage}>
                  <div className="composer-tools">
                    <button type="button" title="Anexar imagem">▧</button>
                    <button type="button" title="Anexar arquivo">⌑</button>
                    <button type="button" title="Inserir link">↗</button>
                  </div>
                  <textarea
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder={operation ? `Digite os dados para ${operation.name}...` : 'Digite sua mensagem...'}
                    rows="3"
                  />
                  <button type="submit" className="send-message-button" aria-label="Enviar mensagem">➤</button>
                </form>
              </section>

              {operation?.numeric ? (
                <aside className="dynamic-panel">
                  <span>Painel Dinâmico</span>
                  <h2>Números em tempo real</h2>
                  <p>Os indicadores e gráficos desta operação aparecerão aqui conforme os dados forem informados no chat.</p>
                  <div className="dynamic-placeholder">
                    <div><strong>—</strong><small>Resultado principal</small></div>
                    <div><strong>—</strong><small>Comparação</small></div>
                    <div><strong>—</strong><small>Projeção</small></div>
                  </div>
                </aside>
              ) : null}
            </div>
          </>
        ) : null}

        {section === 'trash' ? (
          <section className="internal-section">
            <header>
              <div>
                <span>Lixeira</span>
                <h1>Conversas excluídas</h1>
                <p>Restaure uma conversa ou exclua os itens definitivamente.</p>
              </div>
              {trash.length ? <button type="button" onClick={emptyTrash}>Esvaziar lixeira</button> : null}
            </header>
            {trash.length ? (
              <div className="trash-list">
                {trash.map((item) => (
                  <article key={item.id}>
                    <div><strong>{item.title}</strong><small>Excluída em {item.deletedAt}</small></div>
                    <div>
                      <button type="button" onClick={() => restoreConversation(item)}>Restaurar</button>
                      <button type="button" onClick={() => setTrash((current) => current.filter((entry) => entry.id !== item.id))}>Excluir definitivamente</button>
                    </div>
                  </article>
                ))}
              </div>
            ) : <div className="internal-empty-state">A lixeira está vazia.</div>}
          </section>
        ) : null}

        {section === 'billing' ? (
          <section className="internal-section">
            <header>
              <div>
                <span>Faturamento</span>
                <h1>Créditos avulsos</h1>
                <p>Área exclusiva para consultar saldo e comprar pacotes avulsos de créditos.</p>
              </div>
            </header>
            <div className="billing-card">
              <strong>Pacotes de créditos</strong>
              <p>Os valores e quantidades serão conectados aqui após a definição comercial.</p>
              <button type="button" disabled>Comprar créditos</button>
            </div>
          </section>
        ) : null}

        {section === 'settings' ? (
          <section className="internal-section">
            <header>
              <div>
                <span>Configurações</span>
                <h1>Preferências da plataforma</h1>
                <p>Configurações gerais do DomnAI serão organizadas nesta área.</p>
              </div>
            </header>
            <div className="internal-empty-state">Nenhuma configuração disponível nesta etapa.</div>
          </section>
        ) : null}
      </section>
    </main>
  );
}
