from pathlib import Path

jsx_path = Path('/frontend/src/Dashboard.jsx')
source = jsx_path.read_text(encoding='utf-8')

source = source.replace(
    "          const artifacts = result.artifacts || [];",
    "          const artifacts = result.artifacts || [];\n          const sources = Array.isArray(result.sources) ? result.sources : [];",
    1,
)
source = source.replace(
    "                  attachments: artifacts,\n                  processing: false,",
    "                  attachments: artifacts,\n                  sources,\n                  processing: false,",
    1,
)
source = source.replace(
    "        processing: Boolean(message.processing),\n        attachments:",
    "        processing: Boolean(message.processing),\n        sources: (message.sources || []).slice(0, 12).map((item) => ({ title: item.title || item.url, url: item.url })),\n        attachments:",
    1,
)
source = source.replace(
    "          attachments: [],\n          taskId,\n          processing: true,",
    "          attachments: [],\n          sources: [],\n          taskId,\n          processing: true,",
    1,
)

helper = r'''
  function sourceHost(url) {
    try {
      return new URL(url).hostname.replace(/^www\./, '');
    } catch {
      return '';
    }
  }

  function sourceIcon(url) {
    const host = sourceHost(url);
    return host ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(host)}&sz=32` : '';
  }

'''
if 'function sourceHost(url)' not in source:
    marker = '  async function moveLibraryAssetToTrash'
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o ponto de inserção do formatador de fontes.')
    source = source.replace(marker, helper + marker, 1)

old_render = '''                  {message.role === 'assistant' && message.isError ? <button type="button" className="chat-retry-button" onClick={() => retryFailedMessage(message.id)} title="Tentar novamente" aria-label="Tentar novamente" disabled={responding}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7" /></svg></button> : null}
                  {(message.attachments || []).length ?'''
new_render = '''                  {message.role === 'assistant' && message.isError ? <button type="button" className="chat-retry-button" onClick={() => retryFailedMessage(message.id)} title="Tentar novamente" aria-label="Tentar novamente" disabled={responding}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7" /></svg></button> : null}
                  {message.role === 'assistant' && (message.sources || []).length ? <span className="chat-source-icons" aria-label="Fontes da pesquisa">{message.sources.slice(0, 5).map((item, index) => <a key={`${item.url}-${index}`} href={item.url} target="_blank" rel="noreferrer" title={item.title || sourceHost(item.url) || `Fonte ${index + 1}`} aria-label={`Abrir fonte: ${item.title || sourceHost(item.url) || index + 1}`}><img src={sourceIcon(item.url)} alt="" onError={(event) => { event.currentTarget.style.display = 'none'; }} /><span>{index + 1}</span></a>)}</span> : null}
                  {(message.attachments || []).length ?'''
if old_render not in source:
    raise RuntimeError('Não foi possível localizar a área da mensagem para exibir fontes.')
source = source.replace(old_render, new_render, 1)
jsx_path.write_text(source, encoding='utf-8')

css_path = Path('/frontend/src/dashboard-operation-blocks.css')
css = css_path.read_text(encoding='utf-8')
styles = r'''

.chat-source-icons {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin: 6px 0 0 6px;
  vertical-align: middle;
}

.chat-source-icons a {
  position: relative;
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  overflow: hidden;
  border: 1px solid rgba(216, 170, 52, 0.24);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  text-decoration: none;
  transition: border-color 0.16s ease, transform 0.16s ease;
}

.chat-source-icons a:hover,
.chat-source-icons a:focus-visible {
  border-color: rgba(216, 170, 52, 0.7);
  transform: translateY(-1px);
}

.chat-source-icons img {
  width: 15px;
  height: 15px;
  object-fit: contain;
}

.chat-source-icons a > span {
  position: absolute;
  right: -1px;
  bottom: -1px;
  display: none;
  min-width: 10px;
  height: 10px;
  padding: 0 2px;
  border-radius: 5px;
  background: #d8aa34;
  color: #17120a;
  font-size: 7px;
  font-weight: 800;
  line-height: 10px;
  text-align: center;
}

.chat-source-icons a img[style*="display: none"] + span {
  display: block;
}
'''
if '.chat-source-icons {' not in css:
    css += styles
css_path.write_text(css, encoding='utf-8')