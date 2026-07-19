from pathlib import Path


def test_admin_overview_fetches_protected_cutover_status():
    source = Path("frontend/src/AdminOverviewView.jsx").read_text(encoding="utf-8")

    assert "['cutover', '/api/admin/cutover?limit=1000', authorizedHeaders]" in source
    assert "Migração do núcleo" in source
    assert "Validação shadow" in source
    assert "Tráfego novo núcleo" in source
    assert "cutoverSummary.fallbackRate" in source
    assert "data.cutover?.configurationError" in source


def test_admin_overview_does_not_enable_cutover_from_frontend():
    source = Path("frontend/src/AdminOverviewView.jsx").read_text(encoding="utf-8")

    assert "DOMNAI_CUTOVER_ENABLED" not in source
    assert "method: 'POST'" not in source
    assert "method: 'PUT'" not in source
