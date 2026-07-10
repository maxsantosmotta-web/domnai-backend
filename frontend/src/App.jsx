import React from 'react';
import {
  SignInButton,
  SignUpButton,
  UserButton,
  useAuth,
} from '@clerk/clerk-react';
import { Link, Navigate, Route, Routes } from 'react-router-dom';
import DOMNAI_LOGO from './assets/file_00000000b294720eb4facc4b48f63c90.png';

function FooterNavigation() {
  return (
    <footer className="landing-footer" aria-label="Links institucionais">
      <Link to="/sobre">Sobre</Link>
      <Link to="/privacidade">Privacidade</Link>
      <Link to="/termos">Termos</Link>
      <Link to="/ajuda">Ajuda</Link>
    </footer>
  );
}

function Landing() {
  return (
    <main className="landing-page">
      <section className="landing-card" aria-label="Acesso ao DomnAI">
        <img
          className="official-logo"
          src={DOMNAI_LOGO}
          alt="DomnAI — Transforme escolhas em resultados com inteligência."
        />

        <p className="landing-copy">Transforme escolhas em resultados com inteligência.</p>

        <div className="access-actions">
          <SignUpButton mode="modal" forceRedirectUrl="/">
            <button className="primary-button" type="button">Criar conta</button>
          </SignUpButton>

          <SignInButton mode="modal" forceRedirectUrl="/">
            <button className="secondary-button" type="button">Fazer login</button>
          </SignInButton>
        </div>
      </section>

      <FooterNavigation />
    </main>
  );
}

function Dashboard() {
  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <img className="dashboard-logo" src={DOMNAI_LOGO} alt="DomnAI" />
        <UserButton afterSignOutUrl="/" />
      </header>

      <section className="dashboard-content">
        <p className="dashboard-eyebrow">Acesso confirmado</p>
        <h1>Bem-vindo ao DomnAI</h1>
        <p>Transforme escolhas em resultados com inteligência.</p>
      </section>
    </main>
  );
}

function Home() {
  const { isLoaded, isSignedIn } = useAuth();

  if (isLoaded && isSignedIn) {
    return <Dashboard />;
  }

  return <Landing />;
}

const institutionalContent = {
  sobre: {
    title: 'Sobre o DomnAI',
    intro: 'O DomnAI é uma plataforma de apoio à decisão criada para transformar escolhas em resultados com inteligência.',
    sections: [
      ['Nossa proposta', 'Ajudar pessoas a pesquisar, analisar e comparar informações importantes antes de tomar uma decisão.'],
      ['Como ajudamos', 'Organizamos riscos, vantagens, alternativas e pontos de atenção para tornar cada escolha mais clara e segura.'],
      ['Nossa visão', 'Tornar análises inteligentes acessíveis para decisões do dia a dia, negócios, contratos, produtos e serviços.'],
    ],
  },
  privacidade: {
    title: 'Privacidade',
    intro: 'Tratamos dados pessoais e informações enviadas à plataforma com responsabilidade, segurança e transparência.',
    sections: [
      ['Dados de acesso', 'Podemos utilizar informações essenciais de cadastro e autenticação para permitir o uso seguro da plataforma.'],
      ['Conteúdo analisado', 'As informações fornecidas pelo usuário são utilizadas para gerar as análises solicitadas e melhorar a experiência do serviço.'],
      ['Segurança', 'Aplicamos práticas técnicas e operacionais para proteger dados contra acesso indevido, perda ou uso não autorizado.'],
    ],
  },
  termos: {
    title: 'Termos de Uso',
    intro: 'Ao utilizar o DomnAI, o usuário concorda em usar a plataforma de forma responsável e de acordo com estes princípios.',
    sections: [
      ['Uso da plataforma', 'O DomnAI oferece apoio informativo à tomada de decisão e não substitui orientação jurídica, contábil, médica ou financeira profissional.'],
      ['Responsabilidade do usuário', 'O usuário é responsável pelas informações fornecidas e pelas decisões tomadas a partir das análises apresentadas.'],
      ['Evolução do serviço', 'Recursos, planos e funcionalidades poderão evoluir conforme o desenvolvimento da plataforma.'],
    ],
  },
};

function InstitutionalPage({ page }) {
  const content = institutionalContent[page];

  return (
    <main className="content-page">
      <header className="content-header">
        <Link className="brand-link" to="/" aria-label="Voltar para o DomnAI">
          <img src={DOMNAI_LOGO} alt="DomnAI" />
        </Link>
        <Link className="back-link" to="/">Voltar</Link>
      </header>

      <article className="content-card">
        <span className="content-kicker">DomnAI</span>
        <h1>{content.title}</h1>
        <p className="content-intro">{content.intro}</p>

        <div className="content-sections">
          {content.sections.map(([title, text]) => (
            <section key={title}>
              <h2>{title}</h2>
              <p>{text}</p>
            </section>
          ))}
        </div>
      </article>

      <FooterNavigation />
    </main>
  );
}

function HelpPage() {
  const helpSections = [
    ['O que é o DomnAI', 'Uma plataforma de apoio à decisão que ajuda você a pesquisar, comparar, analisar riscos e escolher com mais clareza.'],
    ['Como criar conta', 'Na página inicial, selecione “Criar conta”, informe os dados solicitados e conclua a verificação de acesso.'],
    ['Como fazer login', 'Selecione “Fazer login” e utilize o mesmo método de acesso usado no cadastro.'],
    ['Recuperação de senha', 'Na tela de login, escolha a opção de recuperação e siga as instruções enviadas para seu canal de acesso.'],
    ['Planos', 'A estrutura de planos será apresentada dentro da plataforma conforme os recursos comerciais forem liberados.'],
  ];

  const faq = [
    ['O DomnAI toma decisões por mim?', 'Não. Ele organiza informações, riscos e alternativas para apoiar uma decisão mais consciente.'],
    ['Preciso instalar algum aplicativo?', 'Não. O DomnAI funciona diretamente pelo navegador.'],
    ['Posso usar no celular?', 'Sim. A interface foi preparada para celulares, tablets e computadores.'],
    ['Minhas análises ficam salvas?', 'Os recursos de histórico e salvamento serão exibidos conforme sua conta e plano disponível.'],
  ];

  return (
    <main className="content-page">
      <header className="content-header">
        <Link className="brand-link" to="/" aria-label="Voltar para o DomnAI">
          <img src={DOMNAI_LOGO} alt="DomnAI" />
        </Link>
        <Link className="back-link" to="/">Voltar</Link>
      </header>

      <article className="content-card help-card">
        <span className="content-kicker">Central de ajuda</span>
        <h1>Como podemos ajudar?</h1>
        <p className="content-intro">Encontre orientações rápidas para começar a utilizar o DomnAI.</p>

        <div className="help-grid">
          {helpSections.map(([title, text]) => (
            <section className="help-item" key={title}>
              <h2>{title}</h2>
              <p>{text}</p>
            </section>
          ))}
        </div>

        <section className="faq-section">
          <span className="content-kicker">Perguntas frequentes</span>
          <div className="faq-list">
            {faq.map(([question, answer]) => (
              <details key={question}>
                <summary>{question}</summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>
      </article>

      <FooterNavigation />
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/sobre" element={<InstitutionalPage page="sobre" />} />
      <Route path="/privacidade" element={<InstitutionalPage page="privacidade" />} />
      <Route path="/termos" element={<InstitutionalPage page="termos" />} />
      <Route path="/ajuda" element={<HelpPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
