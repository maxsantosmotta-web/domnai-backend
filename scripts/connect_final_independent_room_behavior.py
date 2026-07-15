from pathlib import Path


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if old not in source:
        raise RuntimeError(f'Não foi possível localizar {label}.')
    return source.replace(old, new, 1)


def append_once(source: str, marker: str, block: str) -> str:
    if marker in source:
        return source
    return source.rstrip() + '\n\n' + block.strip() + '\n'


ROOM_STORAGE_KEY = 'domnai:active-room:v1'

# ---------------------------------------------------------------------------
# Dashboard: restaura Biblioteca, Lixeira ou Faturamento após atualização.
# ---------------------------------------------------------------------------
dashboard_path = Path('/frontend/src/Dashboard.jsx')
dashboard = dashboard_path.read_text(encoding='utf-8')

room_state_helpers = f'''const DOMNAI_ACTIVE_ROOM_KEY = '{ROOM_STORAGE_KEY}';
const DOMNAI_PERSISTED_ROOMS = ['library', 'trash', 'billing'];

function readPersistedDashboardRoom() {{
  try {{
    const room = sessionStorage.getItem(DOMNAI_ACTIVE_ROOM_KEY);
    return DOMNAI_PERSISTED_ROOMS.includes(room) ? room : 'chat';
  }} catch {{
    return 'chat';
  }}
}}

'''

if 'const DOMNAI_ACTIVE_ROOM_KEY' not in dashboard:
    dashboard = replace_once(
        dashboard,
        'const operations = [',
        room_state_helpers + 'const operations = [',
        'os auxiliares de persistência das salas',
    )

dashboard = replace_once(
    dashboard,
    "  const [section, setSection] = useState('chat');",
    '  const [section, setSection] = useState(readPersistedDashboardRoom);',
    'o estado inicial do Dashboard',
)

persistence_effects = '''

  useEffect(() => {
    try {
      if (DOMNAI_PERSISTED_ROOMS.includes(section)) {
        sessionStorage.setItem(DOMNAI_ACTIVE_ROOM_KEY, section);
      } else if (sessionStorage.getItem(DOMNAI_ACTIVE_ROOM_KEY) !== 'profile') {
        sessionStorage.removeItem(DOMNAI_ACTIVE_ROOM_KEY);
      }
    } catch {
      // A navegação continua mesmo sem armazenamento de sessão.
    }
  }, [section]);

  useEffect(() => {
    if (section === 'library') loadLibrary();
    if (section === 'trash') loadTrash();
  }, []);
'''

if 'DOMNAI_PERSISTED_ROOMS.includes(section)' not in dashboard:
    dashboard = replace_once(
        dashboard,
        '  const [conversationReady, setConversationReady] = useState(false);',
        '  const [conversationReady, setConversationReady] = useState(false);' + persistence_effects,
        'o ponto de instalação da persistência das salas',
    )

dashboard = replace_once(
    dashboard,
    '<StandaloneModuleRoom room={standaloneRoom}>',
    '<StandaloneModuleRoom room={standaloneRoom} onClose={openDashboard}>',
    'a conexão do botão Voltar das salas',
)

dashboard_path.write_text(dashboard, encoding='utf-8')


# ---------------------------------------------------------------------------
# Perfil: Voltar discreto, persistência própria e restauração após refresh.
# ---------------------------------------------------------------------------
profile_path = Path('/frontend/src/dashboard-profile-enhancements.js')
profile = profile_path.read_text(encoding='utf-8')
profile = replace_once(
    profile,
    '<button type="button" class="domnai-profile-close">Voltar ao Dashboard</button>',
    '<button type="button" class="domnai-profile-close">Voltar</button>',
    'o texto do botão Voltar do Perfil',
)

if "sessionStorage.setItem('domnai:active-room:v1', 'profile')" not in profile:
    profile = replace_once(
        profile,
        "  document.body.classList.add('domnai-standalone-room-open');\n  return room.querySelector('[data-domnai-profile-host]');",
        "  document.body.classList.add('domnai-standalone-room-open');\n  try { sessionStorage.setItem('domnai:active-room:v1', 'profile'); } catch {}\n  return room.querySelector('[data-domnai-profile-host]');",
        'o registro da sala Perfil',
    )

if "sessionStorage.removeItem('domnai:active-room:v1')" not in profile:
    profile = replace_once(
        profile,
        "function removeProfileStandaloneRoom() {\n  document.querySelector('[data-domnai-profile-room]')?.remove();",
        "function removeProfileStandaloneRoom() {\n  document.querySelector('[data-domnai-profile-room]')?.remove();\n  try { sessionStorage.removeItem('domnai:active-room:v1'); } catch {}",
        'a limpeza da persistência do Perfil',
    )

profile_restore_block = '''
function restorePersistedProfileRoom(attempt = 0) {
  let activeRoom = '';
  try { activeRoom = sessionStorage.getItem('domnai:active-room:v1') || ''; } catch {}
  if (activeRoom !== 'profile' || document.querySelector('[data-domnai-profile-room]')) return;

  if (!window.Clerk?.session || !document.querySelector('.domnai-sidebar')) {
    if (attempt < 80) window.setTimeout(() => restorePersistedProfileRoom(attempt + 1), 100);
    return;
  }

  openDomnAIProfile();
}

window.addEventListener('pageshow', () => window.setTimeout(() => restorePersistedProfileRoom(), 80));
window.setTimeout(() => restorePersistedProfileRoom(), 120);
'''
profile = append_once(profile, 'function restorePersistedProfileRoom(', profile_restore_block)
profile_path.write_text(profile, encoding='utf-8')

profile_back_path = Path('/frontend/src/dashboard-profile-back-fix.js')
profile_back = profile_back_path.read_text(encoding='utf-8')
if "sessionStorage.removeItem('domnai:active-room:v1')" not in profile_back:
    profile_back = replace_once(
        profile_back,
        '  profileRoom?.remove();',
        "  profileRoom?.remove();\n  try { sessionStorage.removeItem('domnai:active-room:v1'); } catch {}",
        'a limpeza da sala Perfil no controlador de retorno',
    )
profile_back_path.write_text(profile_back, encoding='utf-8')


# ---------------------------------------------------------------------------
# FREE: restringe operações/chat e mantém somente Feedback como recurso PREMIUM.
# ---------------------------------------------------------------------------
access_path = Path('/frontend/src/dashboard-access-control.js')
access = access_path.read_text(encoding='utf-8')
access = access.replace(
    'Assine o PREMIUM para utilizar operações, chat, arquivos, Biblioteca e Lixeira.',
    'Assine o PREMIUM para utilizar as operações e o chat.',
)

old_restriction = '''  const operationButton = target.closest('.operations-only button');
  const systemButton = target.closest('.sidebar-system-group button');
  const restrictedSystem = systemButton && (text.includes('Biblioteca') || text.includes('Lixeira') || text.includes('Feedback'));
  const composer = target.closest('.chat-composer, .composer-plus-menu');
  return Boolean(operationButton || restrictedSystem || composer || target.closest('.conversation-options-menu'));'''
new_restriction = '''  const operationButton = target.closest('.operations-only button');
  const systemButton = target.closest('.sidebar-system-group button');
  const restrictedSystem = systemButton && text.includes('Feedback');
  const composer = target.closest('.chat-composer, .composer-plus-menu');
  return Boolean(operationButton || restrictedSystem || composer || target.closest('.conversation-options-menu'));'''
if new_restriction not in access:
    access = replace_once(access, old_restriction, new_restriction, 'a regra de bloqueio do plano FREE')
access_path.write_text(access, encoding='utf-8')

access_css_path = Path('/frontend/src/dashboard-access-control.css')
access_css = access_css_path.read_text(encoding='utf-8')
access_css_overrides = '''
/* Biblioteca, Lixeira, Perfil e Faturamento permanecem acessíveis no FREE. */
html.domnai-access-free .sidebar-system-group button {
  cursor: pointer !important;
}

html.domnai-access-free .sidebar-system-group button:nth-of-type(1)::after,
html.domnai-access-free .sidebar-system-group button:nth-of-type(2)::after {
  display: none !important;
  content: none !important;
}

/* Aviso PREMIUM centralizado no centro real da viewport. */
.domnai-premium-notice {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 100dvh !important;
}

.domnai-premium-notice > section {
  margin: auto !important;
}
'''
access_css = append_once(access_css, 'Aviso PREMIUM centralizado no centro real', access_css_overrides)
access_css_path.write_text(access_css, encoding='utf-8')


# ---------------------------------------------------------------------------
# Perfil: somente o botão Voltar fica branco, discreto e sem caixa.
# ---------------------------------------------------------------------------
profile_css_path = Path('/frontend/src/dashboard-profile-enhancements.css')
profile_css = profile_css_path.read_text(encoding='utf-8')
profile_css_override = '''
.domnai-profile-header .domnai-profile-close {
  min-height: auto !important;
  height: auto !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #ffffff !important;
  box-shadow: none !important;
}

.domnai-profile-header .domnai-profile-close:hover,
.domnai-profile-header .domnai-profile-close:focus-visible {
  color: #e7c35e !important;
}
'''
profile_css = append_once(profile_css, '.domnai-profile-header .domnai-profile-close {', profile_css_override)
profile_css_path.write_text(profile_css, encoding='utf-8')


# ---------------------------------------------------------------------------
# Faturamento: sem plano = Sair; com plano = Voltar + Sair da conta.
# ---------------------------------------------------------------------------
billing_path = Path('/frontend/src/dashboard-billing-enhancements.js')
billing = billing_path.read_text(encoding='utf-8')

old_billing_button = '''      <button type="button" class="billing-back-to-chat${noPlan ? ' billing-approved-back' : ''}" data-billing-action="back-to-chat" ${noPlan ? 'data-approved-billing-back="true"' : ''} aria-label="${noPlan ? 'Sair da conta' : 'Voltar ao chat'}">${noPlan ? 'Sair da conta' : '<span>←</span><span class="billing-back-label">Voltar ao chat</span>'}</button>'''
new_billing_buttons = '''      <div class="billing-room-actions">
        ${noPlan ? '' : '<button type="button" class="billing-room-back" data-billing-action="back-to-dashboard">Voltar</button>'}
        <button type="button" class="billing-room-signout" data-billing-action="sign-out">Sair da conta</button>
      </div>'''
billing = replace_once(billing, old_billing_button, new_billing_buttons, 'os controles do Faturamento')

old_billing_listener = '''  section.querySelector('[data-billing-action="back-to-chat"]')?.addEventListener('click', () => {
    const globalExit = document.querySelector('.global-exit-button');
    if (globalExit) {
      globalExit.click();
      return;
    }
    window.location.hash = '#/';
  });'''
new_billing_listener = '''  section.querySelector('[data-billing-action="back-to-dashboard"]')?.addEventListener('click', () => {
    document.querySelector('.global-exit-button')?.click();
  });

  section.querySelector('[data-billing-action="sign-out"]')?.addEventListener('click', () => {
    window.domnaiSafeSignOut?.();
  });'''
billing = replace_once(billing, old_billing_listener, new_billing_listener, 'os eventos dos controles do Faturamento')
billing_path.write_text(billing, encoding='utf-8')

billing_css_path = Path('/frontend/src/billing-approved-flow-safe.css')
billing_css = billing_css_path.read_text(encoding='utf-8')
billing_css_override = '''
.billing-room-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.billing-room-back {
  min-width: auto !important;
  min-height: auto !important;
  height: auto !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #ffffff !important;
  box-shadow: none !important;
  font-weight: 800 !important;
  cursor: pointer;
}

.billing-room-back:hover,
.billing-room-back:focus-visible {
  color: #e7c35e !important;
}

.billing-room-signout {
  min-height: 40px;
  padding: 0 14px;
  border: 1px solid rgba(205, 76, 76, .34);
  border-radius: 12px;
  background: rgba(120, 28, 28, .12);
  color: #ff9d9d;
  font-weight: 800;
  cursor: pointer;
}

@media (max-width: 620px) {
  .billing-room-actions {
    gap: 10px;
  }

  .billing-room-signout {
    min-height: 38px;
    padding: 0 12px;
  }
}
'''
billing_css = append_once(billing_css, '.billing-room-actions {', billing_css_override)
billing_css_path.write_text(billing_css, encoding='utf-8')
