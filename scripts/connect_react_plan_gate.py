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
  const [screenReady, setScreenReady] = useState(false);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const wait = (delay) => new Promise((resolve) => window.setTimeout(resolve, delay));

    async function loadBillingStatus() {
      setBillingError('');

      for (let attempt = 0; attempt < 20; attempt += 1) {
        try {
          const token = await getToken({ skipCache: attempt > 0 });
          if (!token) {
            await wait(150);
            continue;
          }

          const response = await fetch('/api/billing/status', {
            headers: { Authorization: `Bearer ${token}` },
            cache: 'no-store',
            signal: controller.signal,
          });

          if (response.ok) {
            const status = await response.json();
            if (active) {
              window.__domnaiBillingStatus = status;
              setBillingStatus(status);
            }
            return;
          }

          if (response.status === 401 || response.status === 403) {
            await wait(200 + (attempt * 50));
            continue;
          }

          throw new Error('Não foi possível validar seu cadastro e plano.');
        } catch (error) {
          if (error?.name === 'AbortError') return;
          if (attempt >= 19) {
            if (active) setBillingError(error?.message || 'Não foi possível validar seu acesso.');
            return;
          }
          await wait(200 + (attempt * 50));
        }
      }

      if (active) setBillingError('Sessão não confirmada. Entre novamente.');
    }

    loadBillingStatus();
    return () => {
      active = false;
      controller.abort();
    };
  }, [getToken, userId]);

  useEffect(() => {
    const handleBillingUpdate = (event) => {
      if (!event.detail) return;
      window.__domnaiBillingStatus = event.detail;
      setBillingStatus(event.detail);
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

    if (accessReady) {
      setScreenReady(true);
      return undefined;
    }

    setScreenReady(false);
    let cancelled = false;
    let attempts = 0;
    let timer = null;

    const openBilling = () => {
      if (cancelled) return;

      const billingButton = [...document.querySelectorAll('.sidebar-navigation button')]
        .find((button) => button.textContent.trim().includes('Faturamento'));

      if (billingButton && !billingButton.classList.contains('is-active')) {
        billingButton.click();
      }

      if (document.querySelector('.billing-plans-section')) {
        setScreenReady(true);
        return;
      }

      attempts += 1;
      if (attempts >= 120) {
        setBillingError('Não foi possível abrir o faturamento.');
        return;
      }

      timer = window.setTimeout(openBilling, 50);
    };

    window.requestAnimationFrame(openBilling);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
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
    return <main className="react-plan-gate-page" aria-busy="true" />;
  }

  return (
    <div className="react-plan-gate-wrapper">
      <Dashboard />
      {!screenReady ? <div className="react-plan-gate-overlay" aria-hidden="true" /> : null}
    </div>
  );
}

function Home() {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return <main className="react-plan-gate-page" aria-busy="true" />;
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
