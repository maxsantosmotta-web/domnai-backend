import React, { useMemo, useState } from 'react';
import { UserButton, useAuth } from '@clerk/clerk-react';
import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';
import './dashboard.css';

const tools = [
  { id: 'contrato', title: 'Analisar contrato', description: 'Identifique riscos, obrigações, multas e pontos de atenção.', icon: '▤' },
  { id: 'produto', title: 'Comparar produtos', description: 'Compare custo, benefício, qualidade e alternativas.', icon: '◇' },
  { id: 'orcamento', title: 'Comparar orçamentos', description: 'Descubra qual proposta entrega o melhor valor.', icon: '≋' },
  { id: 'proposta', title: 'Avaliar proposta', description: 'Entenda se as condições são justas antes de aceitar.', icon: '✓' },
  { id: 'negociacao', title: 'Negociar preço', description: 'Organize argumentos para conseguir condições melhores.', icon: '↔' },
  { id: 'empresa', title: 'Abrir empresa', description: 'Compare caminhos, custos e decisões iniciais do negócio.', icon: '⌂' },
  { id: 'decisao-geral', title: 'Outra decisão', description: 'Analise qualquer escolha importante com mais clareza.', icon: '+' },
];

const categoryMap = {
  proposta: 'decisao-geral',
};

function AnalysisResult({ analysis, onReset }) {
  const framework = analysis?.decisionFramework;

  return (
    <section className="analysis-result" aria-live="polite">
      <div className="analysis-result-heading">
        <div>
          <span className="dashboard-kicker">Análise concluída</span>
          <h2>{analysis.category?.name || 'Resultado da análise'}</h2>
        </div>
        <button type="button" className="dashboard-ghost-button" onClick={onReset}>Nova análise</button>
      </div>

      <p className="analysis-summary">{analysis.summary}</p>

      <div className="analysis-columns">
        <article>
          <h3>Riscos</h3>
          <ul>{framework?.risks?.map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
        <article>
          <h3>Vantagens</h3>
          <ul>{framework?.advantages?.map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
        <article>
          <h3>Pontos de atenção</h3>
          <ul>{framework?.attentionPoints?.map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
      </div>

      <article className="analysis-recommendation">
        <span>Recomendação inicial</span>
        <p>{analysis.recommendation}</p>
      </article>

      <p className="analysis-disclaimer">{analysis.disclaimer}</p>
    </section>
  );
}

export default function Dashboard() {
  const { getToken } = useAuth();
  const [selectedTool, setSelectedTool] = useState(null);
  const [question, setQuestion] = useState('');
  const [context, setContext] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const activeTool = useMemo(
    () => tools.find((tool) => tool.id === selectedTool) || null,
    [selectedTool],
  );

  function openTool(tool) {
    setSelectedTool(tool.id);
    setQuestion(tool.title === 'Outra decisão' ? '' : tool.description);
    setContext('');
    setAnalysis(null);
    setError('');
    window.requestAnimationFrame(() => {
      document.getElementById('analysis-workspace')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  function resetWorkspace() {
    setSelectedTool(null);
    setQuestion('');
    setContext('');
    setAnalysis(null);
    setError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (!selectedTool || question.trim().length < 5 || context.trim().length < 20) {
      setError('Explique a decisão e informe um pouco mais de contexto para continuar.');
      return;
    }

    setLoading(true);
    try {
      const token = await getToken();
      const response = await fetch('/api/decisions/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          category: categoryMap[selectedTool] || selectedTool,
          question: question.trim(),
          context: context.trim(),
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || 'Não foi possível concluir a análise.');
      }

      setAnalysis(payload.analysis);
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível concluir a análise.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="dashboard-page dashboard-shell">
      <header className="dashboard-header dashboard-topbar">
        <img className="dashboard-logo" src={DOMNAI_LOGO} alt="DomnAI" />
        <div className="dashboard-account">
          <span>Sua conta</span>
          <UserButton afterSignOutUrl="/" />
        </div>
      </header>

      <section className="dashboard-hero">
        <div>
          <span className="dashboard-kicker">Apoio inteligente para suas escolhas</span>
          <h1>O que você precisa decidir hoje?</h1>
          <p>Escolha uma análise e receba uma visão clara dos riscos, vantagens e próximos passos.</p>
        </div>
        <button type="button" className="dashboard-history-button" disabled>
          Histórico <span>Em breve</span>
        </button>
      </section>

      <section className="dashboard-tools" aria-label="Funcionalidades do DomnAI">
        {tools.map((tool) => (
          <button
            type="button"
            className={`dashboard-tool-card${selectedTool === tool.id ? ' is-active' : ''}`}
            key={tool.id}
            onClick={() => openTool(tool)}
          >
            <span className="dashboard-tool-icon" aria-hidden="true">{tool.icon}</span>
            <span className="dashboard-tool-copy">
              <strong>{tool.title}</strong>
              <small>{tool.description}</small>
            </span>
            <span className="dashboard-tool-arrow" aria-hidden="true">→</span>
          </button>
        ))}
      </section>

      {activeTool ? (
        <section id="analysis-workspace" className="analysis-workspace">
          {analysis ? (
            <AnalysisResult analysis={analysis} onReset={resetWorkspace} />
          ) : (
            <>
              <div className="analysis-workspace-heading">
                <div>
                  <span className="dashboard-kicker">{activeTool.title}</span>
                  <h2>Conte o que você precisa analisar</h2>
                </div>
                <button type="button" className="dashboard-close-workspace" onClick={resetWorkspace} aria-label="Fechar análise">×</button>
              </div>

              <form className="analysis-form" onSubmit={handleSubmit}>
                <label>
                  <span>Qual é a sua dúvida principal?</span>
                  <input
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Exemplo: esta proposta realmente vale a pena?"
                  />
                </label>

                <label>
                  <span>Explique o contexto</span>
                  <textarea
                    value={context}
                    onChange={(event) => setContext(event.target.value)}
                    placeholder="Informe valores, condições, prazos, alternativas e tudo o que pode ajudar na análise."
                    rows="7"
                  />
                </label>

                {error ? <p className="analysis-error" role="alert">{error}</p> : null}

                <button type="submit" className="analysis-submit" disabled={loading}>
                  {loading ? 'Analisando...' : 'Analisar agora'}
                </button>
              </form>
            </>
          )}
        </section>
      ) : null}
    </main>
  );
}
