import React, { useMemo, useRef, useState } from 'react';
import { UserButton, useAuth } from '@clerk/clerk-react';
import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';
import './dashboard.css';
import './dashboard-adjustments.css';

const operations = [
  { id: 'validacao-ideia', name: 'Validação de Ideias e Oportunidades' },
  { id: 'abrir-negocio', name: 'Abrir um Negócio do Zero' },
  { id: 'estrutura-negocio', name: 'Estruturação e Organização Empresarial' },
  { id: 'diagnostico-negocio', name: 'Diagnóstico do Negócio' },
  { id: 'plano-acao', name: 'Plano de Ação Empresarial' },
  { id: 'viabilidade', name: 'Análise de Viabilidade' },
  { id: 'mercado-concorrencia', name: 'Pesquisa de Mercado e Concorrência' },
  { id: 'gestao-financeira', name: 'Gestão Financeira Empresarial' },
  { id: 'precificacao', name: 'Precificação Estratégica' },
  { id: 'metas', name: 'Planejamento de Metas' },
  { id: 'compras', name: 'Cotações e Compras Empresariais' },
  { id: 'fornecedores', name: 'Escolha de Fornecedores' },
  { id: 'negociacao', name: 'Negociação Estratégica' },
  { id: 'dividas', name: 'Análise de Dívidas e Renegociação' },
  { id: 'investimentos', name: 'Análise de Investimentos' },
  { id: 'contrato', name: 'Análise Contratual' },
  { id: 'rescisao', name: 'Cálculo de Rescisão Trabalhista' },
  { id: 'veiculos', name: 'Pesquisa e Comparação de Veículos' },
  { id: 'imoveis', name: 'Análise Imobiliária' },
];

function formatFileSize(size = 0) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function attachmentType(mimeType = '') {
  return mimeType.startsWith('image/') ? 'image' : 'file';
}

export default function Dashboard() {
  const { getToken } = useAuth();
  const cameraInputRef = useRef(null);
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
  const [plusOpen, setPlusOpen] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [uploading, setUploading] = useState(false);

  const [library, setLibrary] = useState([]);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryError, setLibraryError] = useState('');

  const [trash, setTrash] = useState([]);
  const [trashLoading, setTrashLoading] = useState(false);
  const [trashError, setTrashError] = useState('');

  const visibleMessages = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return messages;
    return messages.filter((message) => message.text.toLowerCase().includes(term));
  }, [messages, search]);

  const showExitButton = section !== 'chat';

  async function authorizedFetch(url, options = {}) {
    const token = await getToken();
    return fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        Authorization: `Bearer ${token}`,
      },
    });
  }

  async function loadLibrary() {
    setLibraryLoading(true);
    setLibraryError('');
    try {
      const response = await authorizedFetch('/api/library');
      if (!response.ok) throw new Error('Não foi possível carregar a biblioteca.');
      const data = await response.json();
      setLibrary(data.items || []);
    } catch (error) {
      setLibraryError(error.message || 'Não foi possível carregar a biblioteca.');
    } finally {
      setLibraryLoading(false);
    }
  }

  async function loadTrash() {
    setTrashLoading(true);
    setTrashError('');
    try {
      const response = await authorizedFetch('/api/trash');
      if (!response.ok) throw new Error('Não foi possível carregar a lixeira.');
      const data = await response.json();
      setTrash(data.items || []);
    } catch (error) {
      setTrashError(error.message || 'Não foi possível carregar a lixeira.');
    } finally {
      setTrashLoading(false);
    }
  }

  function selectOperation(item) {
    setActiveOperation(item.id);
    setSection('chat');
    setDraft('');
    setMessages((current) => [...current, { id: Date.now(), role: 'user', text: item.name, attachments: [] }]);
    setSidebarOpen(false);
  }

  function openDashboard() {
    setSection('chat');
    setActiveOperation(null);
    setDraft('');
    setSidebarOpen(false);
    setOptionsOpen(false);
    setPlusOpen(false);
  }

  async function openSection(nextSection) {
    setSection(nextSection);
    setSidebarOpen(false);
    setPlusOpen(false);
    if (nextSection === 'library') await loadLibrary();
    if (nextSection === 'trash') await loadTrash();
  }

  async function saveFileToLibrary(file) {
    const formData = new FormData();
    formData.append('file', file, file.name);
    const response = await authorizedFetch('/api/library', { method: 'POST', body: formData });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Não foi possível salvar ${file.name} na biblioteca.`);
    }
    return response.json();
  }

  async function handleFiles(files) {
    const selected = Array.from(files || []);
    if (!selected.length) return;

    setUploading(true);
    setPlusOpen(false);
    try {
      const savedItems = [];
      for (const file of selected) {
        const saved = await saveFileToLibrary(file);
        savedItems.push({
          id: `attachment-${saved.id}-${Date.now()}`,
          libraryId: saved.id,
          name: saved.name,
          type: attachmentType(saved.mimeType),
          mimeType: saved.mimeType,
          size: saved.sizeBytes,
        });
      }
      setAttachments((current) => [...current, ...savedItems]);
      await loadLibrary();
    } catch (error) {
      window.alert(error.message);
    } finally {
      setUploading(false);
      if (cameraInputRef.current) cameraInputRef.current.value = '';
      if (imageInputRef.current) imageInputRef.current.value = '';
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  function addLink() {
    const url = window.prompt('Cole o link que deseja enviar:');
    if (!url?.trim()) return;
    setAttachments((current) => [...current, { id: `link-${Date.now()}`, name: url.trim(), type: 'link', size: 0 }]);
    setPlusOpen(false);
  }

  function sendMessage(event) {
    event.preventDefault();
    const text = draft.trim();
    if ((!text && attachments.length === 0) || uploading) return;

    setMessages((current) => [...current, {
      id: Date.now(),
      role: 'user',
      text: text || 'Arquivo enviado',
      attachments: [...attachments],
    }]);
    setDraft('');
    setAttachments([]);
    setPlusOpen(false);
  }

  async function moveLibraryAssetToTrash(libraryId) {
    const response = await authorizedFetch(`/api/library/${libraryId}/trash`, { method: 'POST' });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || 'Não foi possível mover o arquivo para a lixeira.');
    }
    return response.json();
  }

  function removeLibraryReferences(libraryId) {
    setAttachments((current) => current.filter((item) => item.libraryId !== libraryId));
    setMessages((current) => current.map((message) => ({
      ...message,
      attachments: (message.attachments || []).filter((item) => item.libraryId !== libraryId),
    })));
    setLibrary((current) => current.filter((item) => item.id !== libraryId));
  }

  async function deleteAttachment(item) {
    try {
      if (item.type === 'link') {
        setAttachments((current) => current.filter((entry) => entry.id !== item.id));
        setMessages((current) => current.map((message) => ({
          ...message,
          attachments: (message.attachments || []).filter((entry) => entry.id !== item.id),
        })));
        return;
      }
      await moveLibraryAssetToTrash(item.libraryId);
      removeLibraryReferences(item.libraryId);
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function deleteConversation() {
    const libraryIds = [...new Set([
      ...messages.flatMap((message) => message.attachments || []),
      ...attachments,
    ].map((item) => item.libraryId).filter(Boolean))];

    try {
      for (const libraryId of libraryIds) await moveLibraryAssetToTrash(libraryId);
      setMessages([]);
      setActiveOperation(null);
      setSearch('');
      setSearchOpen(false);
      setAttachments([]);
      setOptionsOpen(false);
      setPlusOpen(false);
      setLibrary((current) => current.filter((item) => !libraryIds.includes(item.id)));
    } catch (error) {
      window.alert(error.message);
    }
  }

  function refreshConversation() {
    setMessages([]);
    setSearch('');
    setSearchOpen(false);
    setAttachments([]);
    setOptionsOpen(false);
    setPlusOpen(false);
  }

  async function attachLibraryItem(item) {
    try {
      const response = await authorizedFetch(`/api/library/${item.id}/content`);
      if (!response.ok) throw new Error('Não foi possível abrir o arquivo da biblioteca.');
      setAttachments((current) => {
        if (current.some((entry) => entry.libraryId === item.id)) return current;
        return [...current, {
          id: `attachment-${item.id}-${Date.now()}`,
          libraryId: item.id,
          name: item.name,
          type: attachmentType(item.mimeType),
          mimeType: item.mimeType,
          size: item.sizeBytes,
        }];
      });
      setSection('chat');
      setPlusOpen(false);
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function deleteLibraryItem(item) {
    try {
      await moveLibraryAssetToTrash(item.id);
      removeLibraryReferences(item.id);
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function restoreTrashItem(item) {
    try {
      const response = await authorizedFetch(`/api/trash/${item.id}/restore`, { method: 'POST' });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || 'Não foi possível restaurar o arquivo.');
      }
      const restored = await response.json();
      setTrash((current) => current.filter((entry) => entry.id !== item.id));
      setLibrary((current) => [restored, ...current]);
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function permanentlyDeleteTrashItem(itemId) {
    try {
      const response = await authorizedFetch(`/api/trash/${itemId}`, { method: 'DELETE' });
      if (!response.ok && response.status !== 204) throw new Error('Não foi possível excluir o arquivo definitivamente.');
      setTrash((current) => current.filter((entry) => entry.id !== itemId));
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function emptyTrash() {
    try {
      const response = await authorizedFetch('/api/trash', { method: 'DELETE' });
      if (!response.ok && response.status !== 204) throw new Error('Não foi possível esvaziar a lixeira.');
      setTrash([]);
    } catch (error) {
      window.alert(error.message);
    }
  }

  return (
    <main className="domnai-app-shell">
      <input ref={cameraInputRef} className="hidden-file-input" type="file" accept="image/*" capture="environment" onChange={(event) => handleFiles(event.target.files)} />
      <input ref={imageInputRef} className="hidden-file-input" type="file" accept="image/*" multiple onChange={(event) => handleFiles(event.target.files)} />
      <input ref={fileInputRef} className="hidden-file-input" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.csv" multiple onChange={(event) => handleFiles(event.target.files)} />

      <button type="button" className="mobile-menu-button" aria-label="Abrir dashboard" onClick={() => setSidebarOpen(true)}>☰</button>
      <button type="button" className="options-menu-button" aria-label="Abrir opções da conversa" onClick={() => setOptionsOpen((current) => !current)}>⋮</button>
      {showExitButton ? <button type="button" className="global-exit-button" onClick={openDashboard}>← Sair</button> : null}

      {sidebarOpen ? <button className="sidebar-backdrop" type="button" aria-label="Fechar menu" onClick={() => setSidebarOpen(false)} /> : null}
      {optionsOpen ? <button className="options-backdrop" type="button" aria-label="Fechar opções" onClick={() => setOptionsOpen(false)} /> : null}

      <aside className={`domnai-sidebar${sidebarOpen ? ' is-open' : ''}`}>
        <div className="sidebar-brand">
          <img src={DOMNAI_LOGO} alt="DomnAI" />
          <button type="button" className="sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu">×</button>
        </div>

        <nav className="sidebar-navigation" aria-label="Dashboard do DomnAI">
          <button className={section === 'chat' && !activeOperation ? 'is-active' : ''} type="button" onClick={openDashboard}><span>▣</span> Dashboard</button>

          <div className="sidebar-group operations-only">
            <p>Operações</p>
            {operations.map((item) => (
              <button className={activeOperation === item.id && section === 'chat' ? 'is-active' : ''} type="button" key={item.id} onClick={() => selectOperation(item)}>
                <span>›</span> {item.name}
              </button>
            ))}
          </div>

          <div className="sidebar-group sidebar-system-group">
            <p>Sistema</p>
            <button className={section === 'library' ? 'is-active' : ''} type="button" onClick={() => openSection('library')}><span>▤</span> Biblioteca</button>
            <button className={section === 'trash' ? 'is-active' : ''} type="button" onClick={() => openSection('trash')}><span>⌫</span> Lixeira</button>
            <button className={section === 'billing' ? 'is-active' : ''} type="button" onClick={() => openSection('billing')}><span>◈</span> Faturamento</button>
            <button className={section === 'settings' ? 'is-active' : ''} type="button" onClick={() => openSection('settings')}><span>⚙</span> Configurações</button>
          </div>
        </nav>

        <div className="sidebar-profile"><UserButton afterSignOutUrl="/" /><div><strong>Minha conta</strong><small>Perfil e acesso</small></div></div>
      </aside>

      {optionsOpen ? (
        <aside className="conversation-options-menu" aria-label="Opções da conversa">
          <button type="button" onClick={refreshConversation}><span>↻</span> Atualizar conversa</button>
          <button type="button" onClick={() => { setSearchOpen(true); setOptionsOpen(false); }}><span>⌕</span> Buscar na conversa</button>
          <button type="button" className="danger-option" onClick={deleteConversation}><span>♲</span> Excluir conversa</button>
        </aside>
      ) : null}

      <section className="domnai-main-area">
        {section === 'chat' ? (
          <div className="chat-workspace">
            <section className="chat-column">
              {searchOpen ? (
                <label className="inline-chat-search"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Pesquisar por palavra-chave" autoFocus /><button type="button" onClick={() => { setSearchOpen(false); setSearch(''); }}>×</button></label>
              ) : null}

              <div className="chat-messages clean-chat-area">
                {visibleMessages.map((message) => (
                  <article className={`chat-message ${message.role}`} key={message.id}>
                    <span>{message.role === 'assistant' ? 'DomnAI' : 'Você'}</span>
                    <p>{message.text}</p>
                    {(message.attachments || []).length ? (
                      <div className="message-attachments">
                        {message.attachments.map((item) => (
                          <div key={item.id} className="message-attachment">
                            <div><strong>{item.name}</strong>{item.type !== 'link' ? <small>{formatFileSize(item.size)}</small> : null}</div>
                            <button type="button" onClick={() => deleteAttachment(item)}>Excluir</button>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>

              <form className="chat-composer simplified-composer composer-with-plus" onSubmit={sendMessage}>
                {plusOpen ? (
                  <div className="composer-plus-menu">
                    <button type="button" onClick={() => cameraInputRef.current?.click()}><span>◉</span> Câmera</button>
                    <button type="button" onClick={() => imageInputRef.current?.click()}><span>▧</span> Fotos</button>
                    <button type="button" onClick={() => fileInputRef.current?.click()}><span>⌑</span> Arquivos e PDF</button>
                    <button type="button" onClick={() => openSection('library')}><span>▤</span> Biblioteca</button>
                    <button type="button" onClick={addLink}><span>↗</span> Inserir link</button>
                  </div>
                ) : null}

                {attachments.length ? (
                  <div className="attachment-preview">
                    {attachments.map((item) => (
                      <span key={item.id}>{item.name}<button type="button" onClick={() => deleteAttachment(item)}>×</button></span>
                    ))}
                  </div>
                ) : null}

                <button type="button" className="composer-plus-button" aria-label="Adicionar arquivo" onClick={() => setPlusOpen((current) => !current)}>+</button>
                <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={uploading ? 'Salvando na biblioteca...' : 'Digite sua mensagem...'} rows="3" disabled={uploading} />
                <button type="submit" className="send-message-button" aria-label="Enviar mensagem" disabled={uploading}>➤</button>
              </form>
            </section>
          </div>
        ) : null}

        {section === 'library' ? (
          <section className="internal-section">
            <header><div><span>Biblioteca</span><h1>Seus arquivos</h1><p>PDFs, imagens, prints e arquivos enviados ficam disponíveis aqui.</p></div></header>
            {libraryLoading ? <div className="internal-empty-state">Carregando...</div> : null}
            {libraryError ? <div className="internal-empty-state">{libraryError}</div> : null}
            {!libraryLoading && !libraryError && library.length ? (
              <div className="asset-library-grid">
                {library.map((item) => (
                  <article className="asset-library-card" key={item.id}>
                    <div className="asset-type-icon">{item.mimeType?.startsWith('image/') ? '▧' : '⌑'}</div>
                    <div><strong>{item.name}</strong><small>{formatFileSize(item.sizeBytes)} · {new Date(item.createdAt).toLocaleString('pt-BR')}</small></div>
                    <div className="asset-card-actions"><button type="button" onClick={() => attachLibraryItem(item)}>Anexar ao chat</button><button type="button" className="asset-delete-button" onClick={() => deleteLibraryItem(item)}>Excluir</button></div>
                  </article>
                ))}
              </div>
            ) : null}
            {!libraryLoading && !libraryError && !library.length ? <div className="internal-empty-state">A biblioteca está vazia.</div> : null}
          </section>
        ) : null}

        {section === 'trash' ? (
          <section className="internal-section">
            <header><div><span>Lixeira</span><h1>Arquivos excluídos</h1><p>Ao restaurar, o arquivo volta somente para a Biblioteca.</p></div>{trash.length ? <button type="button" onClick={emptyTrash}>Esvaziar lixeira</button> : null}</header>
            {trashLoading ? <div className="internal-empty-state">Carregando...</div> : null}
            {trashError ? <div className="internal-empty-state">{trashError}</div> : null}
            {!trashLoading && !trashError && trash.length ? (
              <div className="trash-list">
                {trash.map((item) => (
                  <article key={item.id}>
                    <div><strong>{item.name}</strong><small>{formatFileSize(item.sizeBytes)} · Excluído em {new Date(item.deletedAt).toLocaleString('pt-BR')}</small></div>
                    <div><button type="button" onClick={() => restoreTrashItem(item)}>Restaurar para Biblioteca</button><button type="button" onClick={() => permanentlyDeleteTrashItem(item.id)}>Excluir definitivamente</button></div>
                  </article>
                ))}
              </div>
            ) : null}
            {!trashLoading && !trashError && !trash.length ? <div className="internal-empty-state">A lixeira está vazia.</div> : null}
          </section>
        ) : null}

        {section === 'billing' ? (
          <section className="internal-section"><header><div><span>Faturamento</span><h1>Créditos avulsos</h1><p>Compra de pacotes avulsos de créditos.</p></div></header><div className="billing-card"><strong>Pacotes de créditos</strong><button type="button" disabled>Comprar créditos</button></div></section>
        ) : null}

        {section === 'settings' ? (
          <section className="internal-section"><header><div><span>Configurações</span><h1>Preferências da plataforma</h1></div></header><div className="internal-empty-state">Nenhuma configuração disponível nesta etapa.</div></section>
        ) : null}
      </section>
    </main>
  );
}
