from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')
old = '<StandaloneModuleRoom room={standaloneRoom}>'
new = '<StandaloneModuleRoom room={standaloneRoom} onClose={openDashboard}>'

if old not in source:
    raise RuntimeError('Não foi possível conectar o retorno das salas independentes.')

path.write_text(source.replace(old, new, 1), encoding='utf-8')
