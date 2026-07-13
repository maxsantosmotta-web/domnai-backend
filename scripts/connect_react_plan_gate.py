from pathlib import Path

path = Path('/frontend/src/App.jsx')
source = path.read_text(encoding='utf-8')

source = source.replace(
    "import React, { useState } from 'react';",
    "import React, { useEffect, useState } from 'react';",
    1,
)

old = '''function Home() {
  const { isLoaded, isSignedIn } = useAuth();

  if (isLoaded && isSignedIn) {
    return <Dashboard />;
  }

  return <Landing />;
}
'''

new = '''function ProtectedDashboard() {
  const { getToken, userId } = useAuth();
  const [billingStatus, setBillingStatus] = useState(null);
  const [billingError, setBillingError] = useState('');
  const [planScreenReady, setPlanScreenReady] = useState(false);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);

    async function loadBillingStatus() {
      try {
        setBillingError('');
        const token = await getToken();
        const response = await fetch('/api/billing/status', {
          headers: { Authorization: `Bearer ${token}` },
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('Não foi possível validar seu plano.');
        const status = await response.json();
        if (active) setBillingStatus(status);
      } catch (error) {
        if (active) setBillingError(error?.name === 'AbortError'
          ? 'A validação do plano demorou mais que o esperado.'
          : error?.message || 'Não foi possível validar seu plano.');
      } finally {
        window.clearTimeout(timeout);
      }
    }

    loadBillingStatus();
    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [getToken, userId]);

  useEffect(() => {
    const handleBillingUpdate = (event) => {
      if (event.detail) setBillingStatus(event.detail);
    };
    const handlePlanReady = () => setPlanScreenReady(true);
    window.addEventListener('domnai:billing-updated', handleBillingUpdate);
    window.addEventListener('domnai:plan-screen-ready', handlePlanReady);
    return () => {
      window.removeEventListener('domnai:billing-updated', handleBillingUpdate);
      window.removeEventListener('domnai:plan-screen-ready', handlePlanReady);
    };
  }, []);

  const planSelected = Boolean(
    billingStatus?.plan && !['unselected', 'free_demo'].includes(billingStatus.plan),
  );

  useEffect(() => {
    if (!billingStatus) return;
    window.__domnaiBillingStatus = billingStatus;
    window.dispatchEvent(new CustomEvent('domnai:billing-updated', { detail: billingStatus }));
    if (!planSelected) setPlanScreenReady(false);
  }, [billingStatus, planSelected]);

  if (billingError) {
    return (
      <main className="react-plan-gate-page" role="alert">
        <section className="react-plan-gate-card">
          <h1>Não foi possível validar seu acesso.</h1>
          <p>{billingError}</p>
          <button type="button" onClick={() => window.location.reload()}>Tentar novamente</button>
          <button type="button" className="secondary" onClick={() => window.domnaiSafeSignOut?.()}>Sair da conta</button>
        </section>
      </main>
    );
  }

  if (!billingStatus) {
    return (
      <main className="react-plan-gate-page" aria-busy="true">
        <section className="react-plan-gate-card">
          <h1>Validando seu acesso...</h1>
          <p>Aguarde enquanto verificamos seu cadastro e plano.</p>
        </section>
      </main>
    );
  }

  if (!planSelected) {
    return (
      <div className="react-plan-gate-wrapper">
        <Dashboard />
        {!planScreenReady ? (
          <div className="react-plan-gate-overlay" aria-busy="true">
            <section className="react-plan-gate-card">
              <h1>Preparando a escolha do plano...</h1>
              <p>Seu acesso só será liberado depois que você escolher FREE ou PREMIUM.</p>
            </section>
          </div>
        ) : null}
      </div>
    );
  }

  return <Dashboard />;
}

function Home() {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return (
      <main className="react-plan-gate-page" aria-busy="true">
        <section className="react-plan-gate-card"><h1>Carregando...</h1></section>
      </main>
    );
  }

  if (isSignedIn) return <ProtectedDashboard />;
  return <Landing />;
}
'''

if old not in source:
    raise RuntimeError('Home original não encontrado para instalar o gate React.')

source = source.replace(old, new, 1)
path.write_text(source, encoding='utf-8')

main_path = Path('/frontend/src/main.jsx')
main_source = main_path.read_text(encoding='utf-8')
css_import = "import './react-plan-gate.css';"
if css_import not in main_source:
    main_source = main_source.replace(
        "import './dashboard-onboarding-enhancements.css';",
        "import './dashboard-onboarding-enhancements.css';\n" + css_import,
        1,
    )
main_path.write_text(main_source, encoding='utf-8')
