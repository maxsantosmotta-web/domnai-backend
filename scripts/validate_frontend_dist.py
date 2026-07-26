from __future__ import annotations

import re
import subprocess
from pathlib import Path


DIST_DIR = Path('/frontend/dist')
INDEX_PATH = DIST_DIR / 'index.html'
OFFICIAL_LOGO_SOURCE = Path('/frontend/src/assets/domnai-logo-oficial-transparente.png')
ICON_192 = DIST_DIR / 'domnai-icon-192.png'
ICON_512 = DIST_DIR / 'domnai-icon-512.png'
ASSET_PATTERN = re.compile(r'''(?:src|href)=["'](?:/)?(assets/[^"']+)["']''')


def _generate_square_icon(size: int, target: Path) -> None:
    safe_size = round(size * 0.88)
    subprocess.run(
        [
            'magick',
            str(OFFICIAL_LOGO_SOURCE),
            '-trim',
            '-resize',
            f'{safe_size}x{safe_size}',
            '-gravity',
            'center',
            '-background',
            'none',
            '-extent',
            f'{size}x{size}',
            str(target),
        ],
        check=True,
    )


def main() -> None:
    if not INDEX_PATH.is_file():
        raise RuntimeError('frontend/dist/index.html não foi gerado.')

    if not OFFICIAL_LOGO_SOURCE.is_file():
        raise RuntimeError('Logo oficial do DomnAI não foi encontrado no frontend.')

    _generate_square_icon(192, ICON_192)
    _generate_square_icon(512, ICON_512)

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

    for icon in (ICON_192, ICON_512):
        if not icon.is_file() or icon.stat().st_size == 0:
            raise RuntimeError(f'Ícone PWA não foi gerado: {icon.name}')

    print(
        'Frontend dist validado: '
        f'{len(assets)} assets, {len(javascript)} JavaScript, {len(stylesheets)} CSS e ícones PWA oficiais.'
    )


if __name__ == '__main__':
    main()
