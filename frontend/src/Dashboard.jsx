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
  { id: 'veiculos', name: 'Pesquisa e Comparação de Veículos' },
  { id: 'imoveis', name: 'Análise Imobiliária' },
];

function formatFileSize(size = 0) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function fileExtension(name = '') {
  return name.includes('.') ? name.split('.').pop().toLowerCase() : '';
}

function attachmentType(mimeType = '', name = '') {
  const extension = fileExtension(name);
  if (mimeType.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'].includes(extension)) return 'image';
  if (mimeType === 'application/pdf' || extension === 'pdf') return 'pdf';
  if (mimeType.includes('word') || mimeType.includes('document') || ['doc', 'docx', 'odt'].includes(extension)) return 'word';
  if (mimeType.includes('sheet') || mimeType.includes('excel') || ['xls', 'xlsx', 'ods', 'csv'].includes(extension)) return 'spreadsheet';
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint') || ['ppt', 'pptx', 'odp'].includes(extension)) return 'presentation';
  if (mimeType.startsWith('text/') || ['txt', 'rtf'].includes(extension)) return 'text';
  if (['zip', 'rar', '7z'].includes(extension)) return 'archive';
  return 'file';
}

function fileTypeLabel(type) {
  const labels = {
    image: 'IMAGEM',
    pdf: 'PDF',
    word: 'WORD',
    spreadsheet: 'PLANILHA',
    presentation: 'APRESENTAÇÃO',
    text: 'TEXTO',
    archive: 'ARQUIVO ZIP',
    file: 'ARQUIVO',
  };
  return labels[type] || 'ARQUIVO';
}

function keepMessage(message) {
  return Boolean(message.text?.trim()) || Boolean(message.attachments?.length);
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
  const [libraryPreviews, setLibraryPreviews] = useState({});

  const [trash, setTrash] = useState([]);
  const [trashLoading, setTrashLoading] = useState(false);
  const [trashError, setTrashError] = useState('');
  const [trashPreviews, setTrashPreviews] = useState({});

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

  async function buildImagePreviewMap(items, basePath) {
    const previews = {};
    await Promise.all(items.map(async (item) => {
      if (attachmentType(item.mimeType, item.name) !== 'image') return;
      try {
        const response = await authorizedFetch(`${basePath}/${item.id}/content`);
        if (!response.ok) return;
        previews[item.id] = URL.createObjectURL(await response.blob());
      } catch {
        // A listagem continua disponível mesmo quando uma miniatura falhar.
      }
    }));
    return previews;
  }

  async function loadLibrary() {
    setLibraryLoading(true);
    setLibraryError('');
    try {
      const response = await authorizedFetch('/api/library');
      if (!response.ok) throw new Error('Não foi possível carregar a biblioteca.');
      const data = await response.json();
      const items = data.items || [];
      setLibrary(items);
      setLibraryPreviews(await buildImagePreviewMap(items, '/api/library'));
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
      const items = data.items || [];
      setTrash(items);
      setTrashPreviews(await buildImagePreviewMap(items, '/api/trash'));
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
          type: attachmentType(saved.mimeType, saved.name),
          mimeType: saved.mimeType,
          size: saved.sizeBytes,
          previewUrl: URL.createObjectURL(file),
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
      text,
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
    setMessages((current) => current
      .map((message) => ({
        ...message,
        attachments: (message.attachments || []).filter((item) => item.libraryId !== libraryId),
      }))
      .filter(keepMessage));
    setLibrary((current) => current.filter((item) => item.id !== libraryId));
    setLibraryPreviews((current) => {
      const next = { ...current };
      delete next[libraryId];
      return next;
    });
  }

  async function deleteAttachment(item) {
    try {
      if (item.type === 'link') {
        setAttachments((current) => current.filter((entry) => entry.id !== item.id));
        setMessages((current) => current
          .map((message) => ({
            ...message,
            attachments: (message.attachments || []).filter((entry) => entry.id !== item.id),
          }))
          .filter(keepMessage));
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
      const blob = await response.blob();
      setAttachments((current) => {
        if (current.some((entry) => entry.libraryId === item.id)) return current;
        return [...current, {
          id: `attachment-${item.id}-${Date.now()}`,
          libraryId: item.id,
          name: item.name,
          type: attachmentType(item.mimeType, item.name),
          mimeType: item.mimeType,
          size: item.sizeBytes,
          previewUrl: URL.createObjectURL(blob),
        }];
      });
      setSection('chat');
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
      setTrash((current) => current.filter((entry) => entry.id !== item.id));
      setTrashPreviews((current) => {
        const next = { ...current };
        delete next[item.id];
        return next;
      });
      await loadLibrary();
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function deleteTrashItem(item) {
    if (!window.confirm(`Excluir definitivamente ${item.name}?`)) return;
    try {
      const response = await authorizedFetch(`/api/trash/${item.id}`, { method: 'DELETE' });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || 'Não foi possível excluir o arquivo definitivamente.');
      }
      setTrash((current) => current.filter((entry) => entry.id !== item.id));
      setTrashPreviews((current) => {
        const next = { ...current };
        delete next[item.id];
        return next;
      });
    } catch (error) {
      window.alert(error.message);
    }
  }

  async function emptyTrash() {
    if (!window.confirm('Esvaziar a lixeira e excluir todos os arquivos definitivamente?')) return;
    try {
      const response = await authorizedFetch('/api/trash', { method: 'DELETE' });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || 'Não foi possível esvaziar a lixeira.');
      }
      setTrash([]);
      setTrashPreviews({});
    } catch (error) {
      window.alert(error.message);
    }
  }

  return (
    <main className="dashboard-shell">
      <button className={`mobile-menu-button ${sidebarOpen ? 'is-open' : ''}`} type="button" onClick={() => setSidebarOpen((current) => !current)} aria-label="Abrir menu">☰</button>
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <button className="brand" type="button" onClick={openDashboard} aria-label="Ir para o início">
          <img src={DOMNAI_LOGO} alt="DomnAI" />
        </button>
        <nav className="operations-list" aria-label="Operações">
          {operations.map((item) => <button className={activeOperation === item.id ? 'active' : ''} key={item.id} type="button" onClick={() => selectOperation(item)}>{item.name}</button>)}
        </nav>
        <nav className="system-menu" aria-label="Sistema">
          <button className={section === 'library' ? 'active' : ''} type="button" onClick={() => openSection('library')}>Biblioteca</button>
          <button className={section === 'trash' ? 'active' : ''} type="button" onClick={() => openSection('trash')}>Lixeira</button>
          <button className={section === 'billing' ? 'active' : ''} type="button" onClick={() => openSection('billing')}>Faturamento</button>
        </nav>
        <div className="sidebar-user"><UserButton showName /></div>
      </aside>

      <section className="workspace">
        {showExitButton ? <button className="exit-button" type="button" onClick={openDashboard}>×</button> : null}

        {section === 'chat' ? <section className="chat-room">
          <header className="chat-toolbar">
            <div>
              <span className="eyebrow">DomnAI</span>
              <h1>{activeOperation ? operations.find((item) => item.id === activeOperation)?.name : 'Painel Inteligente'}</h1>
            </div>
            <div className="chat-toolbar-actions">
              <button type="button" onClick={() => setSearchOpen((current) => !current)}>⌕</button>
              <button type="button" onClick={() => setOptionsOpen((current) => !current)}>⋮</button>
            </div>
            {searchOpen ? <input className="chat-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar na conversa" /> : null}
            {optionsOpen ? <div className="chat-options"><button type="button" onClick={refreshConversation}>Atualizar conversa</button><button type="button" onClick={deleteConversation}>Excluir conversa</button></div> : null}
          </header>

          <div className="messages-area">
            {visibleMessages.length === 0 ? <div className="empty-chat"><img src={DOMNAI_LOGO} alt="" /><p>Selecione uma operação ou envie uma mensagem para começar.</p></div> : null}
            {visibleMessages.map((message) => <article className={`message ${message.role}`} key={message.id}><p>{message.text}</p>{message.attachments?.length ? <div className="message-attachments">{message.attachments.map((item) => <div className="attachment-card" key={item.id}><span>{fileTypeLabel(item.type)}</span><strong>{item.name}</strong><small>{item.type === 'link' ? item.name : formatFileSize(item.size)}</small>{item.previewUrl && item.type === 'image' ? <img src={item.previewUrl} alt={item.name} /> : null}<button type="button" onClick={() => deleteAttachment(item)}>Excluir</button></div>)}</div> : null}</article>)}
          </div>

          <form className="composer" onSubmit={sendMessage}>
            {attachments.length ? <div className="composer-attachments">{attachments.map((item) => <div className="attachment-card" key={item.id}><span>{fileTypeLabel(item.type)}</span><strong>{item.name}</strong><small>{item.type === 'link' ? item.name : formatFileSize(item.size)}</small>{item.previewUrl && item.type === 'image' ? <img src={item.previewUrl} alt={item.name} /> : null}<button type="button" onClick={() => deleteAttachment(item)}>Excluir</button></div>)}</div> : null}
            <div className="composer-row">
              <div className="plus-menu-wrap">
                <button className="plus-button" type="button" onClick={() => setPlusOpen((current) => !current)}>+</button>
                {plusOpen ? <div className="plus-menu"><button type="button" onClick={() => cameraInputRef.current?.click()}>Câmera</button><button type="button" onClick={() => imageInputRef.current?.click()}>Fotos</button><button type="button" onClick={() => fileInputRef.current?.click()}>Arquivos</button><button type="button" onClick={addLink}>Adicionar link</button></div> : null}
              </div>
              <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Digite sua mensagem..." rows="1" />
              <button className="send-button" type="submit" disabled={uploading}>➤</button>
            </div>
            <input ref={cameraInputRef} className="hidden-input" type="file" accept="image/*" capture="environment" onChange={(event) => handleFiles(event.target.files)} />
            <input ref={imageInputRef} className="hidden-input" type="file" accept="image/*" multiple onChange={(event) => handleFiles(event.target.files)} />
            <input ref={fileInputRef} className="hidden-input" type="file" multiple onChange={(event) => handleFiles(event.target.files)} />
          </form>
        </section> : null}

        {section === 'library' ? <section className="internal-section"><h1>Biblioteca</h1><p>Arquivos salvos no DomnAI.</p>{libraryLoading ? <p>Carregando...</p> : null}{libraryError ? <p>{libraryError}</p> : null}<div className="asset-grid">{library.map((item) => <article className="asset-card" key={item.id}>{libraryPreviews[item.id] ? <img src={libraryPreviews[item.id]} alt={item.name} /> : null}<strong>{item.name}</strong><small>{fileTypeLabel(attachmentType(item.mimeType, item.name))} • {formatFileSize(item.sizeBytes)}</small><div><button type="button" onClick={() => attachLibraryItem(item)}>Usar no chat</button><button type="button" onClick={() => moveLibraryAssetToTrash(item.id).then(() => removeLibraryReferences(item.id))}>Mover para lixeira</button></div></article>)}</div></section> : null}
        {section === 'trash' ? <section className="internal-section"><h1>Lixeira</h1><p>Arquivos removidos ficam aqui até a exclusão definitiva.</p>{trashLoading ? <p>Carregando...</p> : null}{trashError ? <p>{trashError}</p> : null}{trash.length ? <button type="button" onClick={emptyTrash}>Esvaziar lixeira</button> : null}<div className="asset-grid">{trash.map((item) => <article className="asset-card" key={item.id}>{trashPreviews[item.id] ? <img src={trashPreviews[item.id]} alt={item.name} /> : null}<strong>{item.name}</strong><small>{fileTypeLabel(attachmentType(item.mimeType, item.name))} • {formatFileSize(item.sizeBytes)}</small><div><button type="button" onClick={() => restoreTrashItem(item)}>Restaurar</button><button type="button" onClick={() => deleteTrashItem(item)}>Excluir definitivamente</button></div></article>)}</div></section> : null}
        {section === 'billing' ? <section className="internal-section"><h1>Faturamento</h1><p>Área reservada para consumo, plano e histórico financeiro.</p></section> : null}
      </section>
    </main>
  );
}
