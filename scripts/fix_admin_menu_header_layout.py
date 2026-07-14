from pathlib import Path

TARGET = Path("/frontend/src/AdminAccessBoundary.jsx")

old_import = "import './admin-profile-shell.css';\n"
new_import = "import './admin-profile-shell.css';\nimport './admin-menu-header-fixes.css';\n"

old_brand = """          <img src={DOMNAI_LOGO} alt="DomnAI" />
          <span>Painel Adm</span>
        </div>

        <nav aria-label="Monitoramento administrativo">
"""

new_brand = """          <img src={DOMNAI_LOGO} alt="DomnAI" />
          <button type="button" className="domnai-admin-brand-back" onClick={onUser}>Voltar</button>
        </div>

        <p className="domnai-admin-section-label">Painel Adm</p>

        <nav aria-label="Monitoramento administrativo">
"""

old_active = "              className={index === 0 ? 'active' : ''}\n"
old_topbar_back = "          <button type=\"button\" className=\"domnai-admin-back-user\" onClick={onUser}>Voltar</button>\n"

source = TARGET.read_text(encoding="utf-8")

checks = {
    "importação dos estilos": (old_import, 1),
    "bloco da marca": (old_brand, 1),
    "destaque ativo": (old_active, 1),
    "botão voltar do conteúdo": (old_topbar_back, 1),
}

for label, (snippet, expected) in checks.items():
    if source.count(snippet) != expected:
        raise SystemExit(f"{label} não encontrado exatamente {expected} vez(es).")

source = source.replace(old_import, new_import, 1)
source = source.replace(old_brand, new_brand, 1)
source = source.replace(old_active, "", 1)
source = source.replace(old_topbar_back, "", 1)
TARGET.write_text(source, encoding="utf-8")

print("Cabeçalho do menu Adm reposicionado sem alterar o restante do painel.")
