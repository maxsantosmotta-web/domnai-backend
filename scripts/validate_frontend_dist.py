from __future__ import annotations

import re
from pathlib import Path


DIST_DIR = Path('/frontend/dist')
INDEX_PATH = DIST_DIR / 'index.html'
ASSET_PATTERN = re.compile(r'''(?:src|href)=["'](?:/)?(assets/[^"']+)["']''')


def main() -> None:
    if not INDEX_PATH.is_file():
        raise RuntimeError('frontend/dist/index.html não foi gerado.')

    html = INDEX_PATH.read_text(encoding='utf-8')
    assets = sorted(set(ASSET_PATTERN.findall(html)))
    if not assets:
        raise RuntimeError('index.html não referencia nenhum asset compilado.')

    missing = [asset for asset in assets if not (DIST_DIR / asset).is_file()]
    if missing:
        raise RuntimeError('Assets referenciados e ausentes: ' + ', '.join(missing))

    javascript = [asset for asset in assets if asset.endswith('.js')]
    stylesheets = [asset for asset in assets if asset.endswith('.css')]
    if not javascript:
        raise RuntimeError('index.html não referencia o bundle JavaScript principal.')

    print(
        'Frontend dist validado: '
        f'{len(assets)} assets, {len(javascript)} JavaScript, {len(stylesheets)} CSS.'
    )


if __name__ == '__main__':
    main()
