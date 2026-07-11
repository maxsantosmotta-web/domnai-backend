import React, { useMemo, useRef, useState } from 'react';
import { UserButton } from '@clerk/clerk-react';
import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';
import './dashboard.css';
import './dashboard-adjustments.css';

const operations = [
  { id: 'validacao-ideia', name: 'Validação de Ideias e Oportunidades', numeric: true },
  { id: 'abrir-negocio', name: 'Abrir um Negócio do Zero', numeric: true },
  { id: 'estrutura-negocio', name: 'Estruturação e Organização Empresarial', numeric: false },
  { id: 'diagnostico-negocio', name: 'Diagnóstico do Negócio', numeric: true },
  { id: 'plano-acao', name: 'Plano de Ação Empresarial', numeric: false },
  { id: 'viabilidade', name: 'Análise de Viabilidade', numeric: true },
  { id: 'mercado-concorrencia', name: 'Pesquisa de Mercado e Concorrência', numeric: true },
  { id: 'gestao-financeira', name: 'Gestão Financeira Empresarial', numeric: true },
  { id: 'precificacao', name: 'Precificação Estratégica', numeric: true },
  { id: 'metas', name: 'Planejamento de Metas', numeric: true },
  { id: 'compras', name: 'Cotações e Compras Empresariais', numeric: true },
  { id: 'fornecedores', name: 'Escolha de Fornecedores', numeric: true },
  { id: 'negociacao', name: 'Negociação Estratégica', numeric: false },
  { id: 'dividas', name: 'Análise de Dívidas e Renegociação', numeric: true },
  { id: 'investimentos', name: 'Análise de Investimentos', numeric: true },
  { id: 'contrato', name: 'Análise Contratual', numeric: false },
  { id: 'rescisao', name: 'Cálculo de Rescisão Trabalhista', numeric: true },
  { id: 'veiculos', name: 'Pesquisa e Comparação de Veículos', numeric: true },
  { id: 'imoveis', name: 'Análise Imobiliária', numeric: true },
];

export default function Dashboard() {
  const imageInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const [section, setSection] = useState('chat');
  const [activeOperation, setActiveOperation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [search, setSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [trash, setTrash] = useState([]);
  const [attachments, setAttachments] = useState([]);

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
  }

  function openSection(nextSection) {
    setSection(nextSection);
    setSidebarOpen(false);
  }

  function handleFiles(files, type) {
    const selected = Array.from(files || []).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      name: file.name,
      type,
    }));
    setAttachments((current) => [...current, ...selected]);
    setOptionsOpen(false);
  }

  function addLink() {
    const url = window.prompt('Cole o link que deseja enviar:');
    if (!url?.trim()) return;
    setAttachments((current) => [
      ...current,
      { id: `link-${Date.now()}`, name: url.trim(), type: 'link' },
    ]);
    setOptionsOpen(false);
  }

  function sendMessage(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text && attachments.length === 0) return;

    const attachmentText = attachments.length
      ? `\n\nAnexos: ${attachments.map((item) => item.name).join(', ')}`
      : '';

    setMessages((current) => [
      ...current,
      { id: Date.now(), role: 'user', text: `${text || 'Arquivo enviado'}${attachmentText}` },
    ]);
    setDraft('');
    setAttachments([]);
  }

  function deleteConversation() {
    if (messages.length) {
      setTrash((current) => [
        { id: Date.now(), title: operation?.name || 'Conversa geral', messages, deletedAt: new Date().toLocaleString('pt-BR') },
        ...current,
      ]);
    }
    setMessages([]);
    setActiveOperation(null);
    setSearch('');
    setSearchOpen(false);
    setAttachments([]);
    setOptionsOpen(false);
  }

  function refreshConversation() {
    setMessages([]);
    setSearch('');
    setSearchOpen(false);
    setAttachments([]);
    setOptionsOpen(false);
  }

  function restoreConversation(item) {
    setMessages(item.messages);
    setTrash((current) => current.filter((entry) => entry.id !== item.id));
    setSection('chat');
  }

  return (
    <main className="domnai-app-shell">
      <input ref={imageInputRef} className="hidden-file-input" type="file" accept="image/*" multiple onChange={(event) => handleFiles(event.target.files, 'image')} />
      <input ref={fileInputRef} className="hidden-file-input" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.csv" multiple onChange={(event) => handleFiles(event.target.files, 'file')} />

      <button type="button" className="mobile-menu-button" aria-label="Abrir dashboard" onClick={() => setSidebarOpen(true)}>☰</button>
      <button type="button" className="options-menu-button" aria-label="Abrir opções da conversa" onClick={() => setOptionsOpen((current) => !current)}>⋮</button>

      {sidebarOpen ? <button className="sidebar-backdrop" type="button" aria-label="Fechar menu" onClick={() => setSidebarOpen(false)} /> : null}
      {optionsOpen ? <button className="options-backdrop" type="button" aria-label="Fechar opções" onClick={() => setOptionsOpen(false)} /> : null}

      <aside className={`domnai-sidebar${sidebarOpen ? ' is-open' : ''}`}>
        <div className="sidebar-brand">
          <img src={DOMNAI_LOGO} alt="DomnAI" />
          <button type="button" className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu">×</button>
        </div>

        <nav className="sidebar-navigation" aria-label="Dashboard do DomnAI">
          <button className={section === 'chat' ? 'is-active' : ''} type="button" onClick={() => openSection('chat')}>
            <span>▣</span> Dashboard
          </button>

          <div className="sidebar-group operations-only">
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
            <button className={section === 'trash' ? 'is-active' : ''} type="button" onClick={() => openSection('trash')}>
              <span>⌫</span> Lixeira
            </button>
            <button className={section === 'billing' ? 'is-active' : ''} type="button" onClick={() => openSection('billing')}>
              <span>◈</span> Faturamento
            </button>
            <button className={section === 'settings' ? 'is-active' : ''} type="button" onClick={() => openSection('settings')}>
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

      {optionsOpen ? (
        <aside className="conversation-options-menu" aria-label="Opções da conversa">
          <button type="button" onClick={refreshConversation}><span>↻</span> Atualizar conversa</button>
          <button type="button" onClick={() => { setSearchOpen(true); setOptionsOpen(false); }}><span>⌕</span> Buscar na conversa</button>
          <button type="button" onClick={() => imageInputRef.current?.click()}><span>▧</span> Enviar imagem ou print</button>
          <button type="button" onClick={() => fileInputRef.current?.click()}><span>⌑</span> Enviar PDF ou arquivo</button>
          <button type="button" onClick={addLink}><span>↗</span> Inserir link</button>
          <button type="button" className="danger-option" onClick={deleteConversation}><span>♲</span> Excluir conversa</button>
        </aside>
      ) : null}

      <section className="domnai-main-area">
        {section === 'chat' ? (
          <div className={`chat-workspace${operation?.numeric ? ' has-dynamic-panel' : ''}`}>
            <section className="chat-column">
              {searchOpen ? (
                <label className="inline-chat-search">
                  <span aria-hidden="true">⌕</span>
                  <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Pesquisar por palavra-chave" autoFocus />
                  <button type="button" onClick={() => { setSearchOpen(false); setSearch(''); }}>×</button>
                </label>
              ) : null}

              <div className="chat-messages clean-chat-area">
                {visibleMessages.map((message) => (
                  <article className={`chat-message ${message.role}`} key={message.id}>
                    <span>{message.role === 'assistant' ? 'DomnAI' : 'Você'}</span>
                    <p>{message.text}</p>
                    {message.role === 'assistant' ? <button type="button" onClick={() => navigator.clipboard?.writeText(message.text)}>Copiar</button> : null}
                  </article>
                ))}
              </div>

              <form className="chat-composer simplified-composer" onSubmit={sendMessage}>
                {attachments.length ? (
                  <div className="attachment-preview">
                    {attachments.map((item) => (
                      <span key={item.id}>{item.name}<button type="button" onClick={() => setAttachments((current) => current.filter((entry) => entry.id !== item.id))}>×</button></span>
                    ))}
                  </div>
                ) : null}
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder={operation ? operation.name : 'Digite sua mensagem...'}
                  rows="3"
                />
                <button type="submit" className="send-message-button" aria-label="Enviar mensagem">➤</button>
              </form>
            </section>

            {operation?.numeric ? (
              <aside className="dynamic-panel compact-dynamic-panel">
                <div className="live-chart-placeholder" aria-label="Gráfico em tempo real">
                  <div className="chart-bar" style={{ height: '28%' }} />
                  <div className="chart-bar" style={{ height: '48%' }} />
                  <div className="chart-bar" style={{ height: '68%' }} />
                  <div className="chart-bar" style={{ height: '88%' }} />
                </div>
              </aside>
            ) : null}
          </div>
        ) : null}

        {section === 'trash' ? (
          <section className="internal-section">
            <header><div><span>Lixeira</span><h1>Conversas excluídas</h1></div>{trash.length ? <button type="button" onClick={() => setTrash([])}>Esvaziar lixeira</button> : null}</header>
            {trash.length ? (
              <div className="trash-list">
                {trash.map((item) => (
                  <article key={item.id}>
                    <div><strong>{item.title}</strong><small>Excluída em {item.deletedAt}</small></div>
                    <div><button type="button" onClick={() => restoreConversation(item)}>Restaurar</button><button type="button" onClick={() => setTrash((current) => current.filter((entry) => entry.id !== item.id))}>Excluir definitivamente</button></div>
                  </article>
                ))}
              </div>
            ) : <div className="internal-empty-state">A lixeira está vazia.</div>}
          </section>
        ) : null}

        {section === 'billing' ? (
          <section className="internal-section">
            <header><div><span>Faturamento</span><h1>Créditos avulsos</h1><p>Compra de pacotes avulsos de créditos.</p></div></header>
            <div className="billing-card"><strong>Pacotes de créditos</strong><button type="button" disabled>Comprar créditos</button></div>
          </section>
        ) : null}

        {section === 'settings' ? (
          <section className="internal-section">
            <header><div><span>Configurações</span><h1>Preferências da plataforma</h1></div></header>
            <div className="internal-empty-state">Nenhuma configuração disponível nesta etapa.</div>
          </section>
        ) : null}
      </section>
    </main>
  );
}
