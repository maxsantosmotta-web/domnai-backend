from pathlib import Path

path = Path('/frontend/src/Dashboard.jsx')
source = path.read_text(encoding='utf-8')

css_import = "import './mobile-chat-keyboard.css';"
if css_import not in source:
    marker = "import './dashboard-adjustments.css';"
    if marker not in source:
        raise RuntimeError('Não foi possível localizar os estilos-base do Dashboard.')
    source = source.replace(marker, marker + "\n" + css_import, 1)

viewport_effect = r'''
  useEffect(() => {
    const viewport = window.visualViewport;
    const coarsePointer = window.matchMedia?.('(pointer: coarse)')?.matches;
    if (!viewport || !coarsePointer || section !== 'chat') return undefined;

    const root = document.documentElement;
    const composer = operationComposerRef.current;
    const textarea = composer?.querySelector('textarea');
    let settleTimer = null;

    const keepComposerVisible = () => {
      const visibleHeight = Math.max(320, Math.round(viewport.height));
      const keyboardInset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
      root.style.setProperty('--domnai-chat-visible-height', `${visibleHeight}px`);
      root.classList.add('domnai-mobile-chat-viewport');
      root.classList.toggle('domnai-keyboard-open', keyboardInset > 120 || document.activeElement === textarea);

      if (document.activeElement === textarea) {
        window.requestAnimationFrame(() => {
          composer?.scrollIntoView({ block: 'end', inline: 'nearest' });
          const messageArea = composer?.previousElementSibling;
          if (messageArea?.classList?.contains('clean-chat-area')) {
            messageArea.scrollTop = messageArea.scrollHeight;
          }
        });
      }
    };

    const onFocus = () => {
      keepComposerVisible();
      window.clearTimeout(settleTimer);
      settleTimer = window.setTimeout(keepComposerVisible, 180);
    };

    const onBlur = () => {
      window.clearTimeout(settleTimer);
      settleTimer = window.setTimeout(keepComposerVisible, 120);
    };

    keepComposerVisible();
    viewport.addEventListener('resize', keepComposerVisible);
    viewport.addEventListener('scroll', keepComposerVisible);
    window.addEventListener('orientationchange', keepComposerVisible);
    textarea?.addEventListener('focus', onFocus);
    textarea?.addEventListener('blur', onBlur);

    return () => {
      window.clearTimeout(settleTimer);
      viewport.removeEventListener('resize', keepComposerVisible);
      viewport.removeEventListener('scroll', keepComposerVisible);
      window.removeEventListener('orientationchange', keepComposerVisible);
      textarea?.removeEventListener('focus', onFocus);
      textarea?.removeEventListener('blur', onBlur);
      root.classList.remove('domnai-mobile-chat-viewport', 'domnai-keyboard-open');
      root.style.removeProperty('--domnai-chat-visible-height');
    };
  }, [section]);

'''

if "domnai-mobile-chat-viewport" not in source:
    markers = (
        "  async function selectOperation(item) {",
        "  function selectOperation(item) {",
    )
    marker = next((candidate for candidate in markers if candidate in source), None)
    if marker is None:
        raise RuntimeError('Não foi possível localizar o ponto seguro antes da seleção de operação.')
    source = source.replace(marker, viewport_effect + marker, 1)

path.write_text(source, encoding='utf-8')
