from pathlib import Path

path = Path('/frontend/src/dashboard-access-control.css')
source = path.read_text(encoding='utf-8')
marker = '/* Centralização absoluta do aviso PREMIUM na viewport. */'

if marker not in source:
    source = source.rstrip() + '''

/* Centralização absoluta do aviso PREMIUM na viewport. */
.domnai-premium-notice > section {
  position: fixed !important;
  left: 50vw !important;
  top: 50dvh !important;
  right: auto !important;
  bottom: auto !important;
  width: min(460px, calc(100vw - 36px)) !important;
  max-width: calc(100vw - 36px) !important;
  margin: 0 !important;
  transform: translate(-50%, -50%) !important;
}
'''

path.write_text(source, encoding='utf-8')
