import React from 'react';

function formatError(error) {
  if (!error) return 'Erro desconhecido durante a inicialização.';
  return error.message || String(error);
}

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('[DomnAI] Erro de renderização não tratado:', error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <main className="runtime-error-page" role="alert">
        <section className="runtime-error-card">
          <h1>DomnAI</h1>
          <h2>Não foi possível concluir a abertura.</h2>
          <p>{formatError(this.state.error)}</p>
          <button type="button" onClick={() => window.location.reload()}>
            Tentar novamente
          </button>
        </section>
      </main>
    );
  }
}
