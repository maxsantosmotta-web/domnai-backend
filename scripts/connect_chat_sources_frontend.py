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

'''
if 'function sourceHost(url)' not in source:
    marker = '  async function moveLibraryAssetToTrash'
    if marker not in source:
        raise RuntimeError('Não foi possível localizar o ponto de inserção do formatador de fontes.')
    source = source.replace(marker, helper + marker, 1)

old_render = '''                  {message.role === 'assistant' && message.isError ? <button type="button" className="chat-retry-button" onClick={() => retryFailedMessage(message.id)} title="Tentar novamente" aria-label="Tentar novamente" disabled={responding}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7" /></svg></button> : null}
                  {(message.attachments || []).length ?'''
new_render = '''                  {message.role === 'assistant' && message.isError ? <button type="button" className="chat-retry-button" onClick={() => retryFailedMessage(message.id)} title="Tentar novamente" aria-label="Tentar novamente" disabled={responding}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7" /></svg></button> : null}
                  {message.role === 'assistant' && (message.sources || []).length ? <div className="chat-sources"><strong>Fontes consultadas</strong><div>{message.sources.slice(0, 5).map((item, index) => <a key={`${item.url}-${index}`} href={item.url} target="_blank" rel="noreferrer"><span>{item.title || sourceHost(item.url) || `Fonte ${index + 1}`}</span><small>{sourceHost(item.url)}</small><b aria-hidden="true">↗</b></a>)}</div></div> : null}
                  {(message.attachments || []).length ?'''
if old_render not in source:
    raise RuntimeError('Não foi possível localizar a área da mensagem para exibir fontes.')
source = source.replace(old_render, new_render, 1)
jsx_path.write_text(source, encoding='utf-8')

css_path = Path('/frontend/src/dashboard-operation-blocks.css')
css = css_path.read_text(encoding='utf-8')
styles = r'''

.chat-sources {
  display: grid;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(216, 170, 52, 0.18);
}

.chat-sources > strong {
  color: #d8aa34;
  font-size: 0.76rem;
  letter-spacing: 0.04em;
}

.chat-sources > div {
  display: grid;
  gap: 6px;
}

.chat-sources a {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 2px 10px;
  align-items: center;
  padding: 7px 9px;
  border: 1px solid rgba(216, 170, 52, 0.16);
  border-radius: 10px;
  color: inherit;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.025);
}

.chat-sources a span {
  overflow: hidden;
  color: #f5e8bd;
  font-size: 0.82rem;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-sources a small {
  overflow: hidden;
  color: rgba(255, 255, 255, 0.52);
  font-size: 0.68rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-sources a b {
  grid-column: 2;
  grid-row: 1 / span 2;
  color: #d8aa34;
  font-size: 0.78rem;
  font-weight: 700;
}
'''
if '.chat-sources {' not in css:
    css += styles
css_path.write_text(css, encoding='utf-8')
