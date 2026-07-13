from pathlib import Path


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if old not in source:
        raise RuntimeError(f'Não foi possível localizar {label}.')
    return source.replace(old, new, 1)


# Biblioteca, Lixeira e Faturamento: preserva o JSX atual e apenas muda o local de renderização.
dashboard_path = Path('/frontend/src/Dashboard.jsx')
dashboard = dashboard_path.read_text(encoding='utf-8')

room_import = "import StandaloneModuleRoom from './StandaloneModuleRoom';"
if room_import not in dashboard:
    dashboard = replace_once(
        dashboard,
        "import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';",
        "import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';\n" + room_import,
        'a importação do portal de módulos',
    )

lines = dashboard.splitlines()
room_lines = {}
remaining_lines = []
for line in lines:
    matched = False
    for room_name in ('library', 'trash', 'billing'):
        if f"{{section === '{room_name}' ?" in line:
            if room_name in room_lines:
                raise RuntimeError(f'O módulo {room_name} apareceu mais de uma vez no Dashboard.')
            room_lines[room_name] = line.replace(
                f"section === '{room_name}'",
                f"standaloneRoom === '{room_name}'",
                1,
            )
            matched = True
            break
    if not matched:
        remaining_lines.append(line)

missing_rooms = [name for name in ('library', 'trash', 'billing') if name not in room_lines]
if missing_rooms:
    raise RuntimeError(f'Não foi possível localizar os módulos: {", ".join(missing_rooms)}.')

dashboard = '\n'.join(remaining_lines) + '\n'

standalone_state = "  const standaloneRoom = ['library', 'trash', 'billing'].includes(section) ? section : null;"
if standalone_state not in dashboard:
    dashboard = replace_once(
        dashboard,
        "  const showExitButton = section !== 'chat';",
        "  const showExitButton = section !== 'chat';\n" + standalone_state,
        'o estado de navegação do Dashboard',
    )

room_block = """      {standaloneRoom ? (
        <StandaloneModuleRoom room={standaloneRoom}>
%s
        </StandaloneModuleRoom>
      ) : null}
""" % '\n'.join(room_lines[name] for name in ('library', 'trash', 'billing'))

closing_anchor = "      </section>\n    </main>"
closing_index = dashboard.rfind(closing_anchor)
if closing_index == -1:
    raise RuntimeError('Não foi possível localizar o fechamento principal do Dashboard.')

dashboard = (
    dashboard[:closing_index]
    + "      </section>\n"
    + room_block
    + "    </main>"
    + dashboard[closing_index + len(closing_anchor):]
)

dashboard_path.write_text(dashboard, encoding='utf-8')


# Minha conta / Perfil: reutiliza integralmente o HTML atual em um host fora do Dashboard.
profile_path = Path('/frontend/src/dashboard-profile-enhancements.js')
profile = profile_path.read_text(encoding='utf-8')

profile_helpers = """function ensureProfileStandaloneRoom() {
  let room = document.querySelector('[data-domnai-profile-room]');
  if (!room) {
    room = document.createElement('div');
    room.className = 'domnai-standalone-room domnai-profile-standalone-room';
    room.setAttribute('data-domnai-standalone-room', 'profile');
    room.setAttribute('data-domnai-profile-room', 'true');
    room.innerHTML = '<div class="domnai-standalone-room-main" data-domnai-profile-host="true"></div>';
    document.body.appendChild(room);
  }
  document.documentElement.classList.add('domnai-standalone-room-open');
  document.body.classList.add('domnai-standalone-room-open');
  return room.querySelector('[data-domnai-profile-host]');
}

function removeProfileStandaloneRoom() {
  document.querySelector('[data-domnai-profile-room]')?.remove();
  if (!document.querySelector('[data-domnai-standalone-room]')) {
    document.documentElement.classList.remove('domnai-standalone-room-open');
    document.body.classList.remove('domnai-standalone-room-open');
  }
}

"""

if 'function ensureProfileStandaloneRoom()' not in profile:
    marker = 'function restoreDashboardFromProfile() {'
    marker_index = profile.find(marker)
    if marker_index == -1:
        raise RuntimeError('Não foi possível localizar o retorno do Perfil.')
    profile = profile[:marker_index] + profile_helpers + profile[marker_index:]

profile = replace_once(
    profile,
    """function restoreDashboardFromProfile() {
  document.querySelector('[data-domnai-profile-page]')?.remove();
  document.querySelector('.domnai-main-area')?.classList.remove('profile-page-open');
  [...document.querySelectorAll('.sidebar-navigation button')].find((button) => button.textContent.trim().includes('Dashboard'))?.click();
}
""",
    """function restoreDashboardFromProfile() {
  document.querySelector('[data-domnai-profile-page]')?.remove();
  document.querySelector('.domnai-main-area')?.classList.remove('profile-page-open');
  removeProfileStandaloneRoom();
  [...document.querySelectorAll('.sidebar-navigation button')].find((button) => button.textContent.trim().includes('Dashboard'))?.click();
}
""",
    'a função de fechar o Perfil',
)

profile = replace_once(
    profile,
    """function renderProfileImmediately(profile, avatarUrl) {
  const mainArea = document.querySelector('.domnai-main-area');
  if (!mainArea) return;
  mainArea.querySelector('[data-domnai-profile-page]')?.remove();
  mainArea.insertAdjacentHTML('beforeend', profilePageHtml(profile || {}, avatarUrl || ''));
  bindProfilePage();
}
""",
    """function renderProfileImmediately(profile, avatarUrl) {
  const host = document.querySelector('[data-domnai-profile-host]') || ensureProfileStandaloneRoom();
  if (!host) return;
  host.querySelector('[data-domnai-profile-page]')?.remove();
  host.insertAdjacentHTML('beforeend', profilePageHtml(profile || {}, avatarUrl || ''));
  bindProfilePage();
}
""",
    'a renderização do Perfil',
)

profile = replace_once(
    profile,
    """async function openDomnAIProfile() {
  const mainArea = document.querySelector('.domnai-main-area');
  if (!mainArea) return;

  document.querySelector('[data-domnai-profile-page]')?.remove();
  mainArea.classList.add('profile-page-open');

  const cachedProfile = readProfileCache() || {
    fullName: window.Clerk?.user?.fullName || window.Clerk?.user?.firstName || '',
  };
  renderProfileImmediately(cachedProfile, currentSidebarAvatarUrl());
  window.requestAnimationFrame(refreshDomnAIProfileSilently);
}
""",
    """async function openDomnAIProfile() {
  const host = ensureProfileStandaloneRoom();
  if (!host) return;

  document.querySelector('[data-domnai-profile-page]')?.remove();

  const cachedProfile = readProfileCache() || {
    fullName: window.Clerk?.user?.fullName || window.Clerk?.user?.firstName || '',
  };
  renderProfileImmediately(cachedProfile, currentSidebarAvatarUrl());
  window.requestAnimationFrame(refreshDomnAIProfileSilently);
}
""",
    'a abertura do Perfil',
)

profile_path.write_text(profile, encoding='utf-8')


# O controlador de retorno do Perfil usa captura de evento; ele também precisa remover a sala.
profile_back_path = Path('/frontend/src/dashboard-profile-back-fix.js')
profile_back = profile_back_path.read_text(encoding='utf-8')

if "const profileRoom = document.querySelector('[data-domnai-profile-room]');" not in profile_back:
    profile_back = replace_once(
        profile_back,
        """  const page = document.querySelector('[data-domnai-profile-page]');
  const mainArea = document.querySelector('.domnai-main-area');
""",
        """  const page = document.querySelector('[data-domnai-profile-page]');
  const mainArea = document.querySelector('.domnai-main-area');
  const profileRoom = document.querySelector('[data-domnai-profile-room]');
""",
        'o controlador de retorno do Perfil',
    )

    profile_back = replace_once(
        profile_back,
        """  if (page?.parentNode && page.parentNode.contains(page)) {
    page.parentNode.removeChild(page);
  }

  window.requestAnimationFrame(() => {
""",
        """  if (page?.parentNode && page.parentNode.contains(page)) {
    page.parentNode.removeChild(page);
  }
  profileRoom?.remove();
  if (!document.querySelector('[data-domnai-standalone-room]')) {
    document.documentElement.classList.remove('domnai-standalone-room-open');
    document.body.classList.remove('domnai-standalone-room-open');
  }

  window.requestAnimationFrame(() => {
""",
        'a remoção da sala do Perfil',
    )

profile_back_path.write_text(profile_back, encoding='utf-8')
