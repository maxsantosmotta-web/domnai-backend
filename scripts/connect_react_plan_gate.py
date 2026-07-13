from pathlib import Path

path = Path('/frontend/src/App.jsx')
source = path.read_text(encoding='utf-8')

source = source.replace(
    "import React, { useState } from 'react';",
    "import React, { useEffect, useState } from 'react';",
    1,
)

if 'function ProtectedDashboard()' not in source:
    start = source.find('function Home() {')
    end = source.find('\nconst institutionalContent = {', start)
    if start == -1 or end == -1:
        raise RuntimeError('Não foi possível localizar o bloco Home em App.jsx.')

    replacement = '''function ProtectedDashboard() {
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
        if (!token) throw new Error('Sessão não encontrada.');
        const response = await fetch('/api/billing/status', {
          headers: { Authorization: `Bearer ${token}` },
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('Não foi possível validar seu cadastro e plano.');
        const status = await response.json();
        if (active) setBillingStatus(status);
      } catch (error) {
        if (active) setBillingError(error?.name === 'AbortError'
          ? 'A validação do acesso demorou mais que o esperado.'
          : error?.message || 'Não foi possível validar seu acesso.');
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
    window.addEventListener('domnai:billing-updated', handleBillingUpdate);
    return () => window.removeEventListener('domnai:billing-updated', handleBillingUpdate);
  }, []);

  const planSelected = Boolean(
    billingStatus?.plan && !['unselected', 'free_demo'].includes(billingStatus.plan),
  );
  const profileCompleted = Boolean(billingStatus?.profileCompleted);
  const accessReady = planSelected && profileCompleted;

  useEffect(() => {
    if (!billingStatus) return undefined;
    window.__domnaiBillingStatus = billingStatus;
    if (accessReady) return undefined;

    setPlanScreenReady(false);
    let attempts = 0;
    const interval = window.setInterval(() => {
      attempts += 1;
      const ready = Boolean(document.querySelector('.billing-plans-section'));
      if (ready || attempts >= 80) {
        setPlanScreenReady(ready);
        window.clearInterval(interval);
      }
    }, 100);
    return () => window.clearInterval(interval);
  }, [billingStatus, accessReady]);

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

  if (!accessReady) {
    return (
      <div className="react-plan-gate-wrapper">
        <Dashboard />
        {!planScreenReady ? (
          <div className="react-plan-gate-overlay" aria-busy="true">
            <section className="react-plan-gate-card">
              <h1>Preparando seu acesso...</h1>
              <p>O Dashboard só será liberado depois que você completar o cadastro e escolher FREE ou PREMIUM.</p>
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

    source = source[:start] + replacement + source[end:]

path.write_text(source, encoding='utf-8')

main_path = Path('/frontend/src/main.jsx')
main_source = main_path.read_text(encoding='utf-8')
css_import = "import './react-plan-gate.css';"
if css_import not in main_source:
    anchor = "import './dashboard-onboarding-enhancements.css';"
    if anchor not in main_source:
        raise RuntimeError('Importação de onboarding não encontrada em main.jsx.')
    main_source = main_source.replace(anchor, anchor + '\n' + css_import, 1)
main_path.write_text(main_source, encoding='utf-8')
