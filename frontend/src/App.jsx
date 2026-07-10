import React, { useState } from 'react';
import {
  AuthenticateWithRedirectCallback,
  UserButton,
  useAuth,
  useSignIn,
  useSignUp,
} from '@clerk/clerk-react';
import { Link, Navigate, Route, Routes } from 'react-router-dom';
import DOMNAI_LOGO from './assets/domnai-logo-oficial-transparente.png';

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

function getClerkError(error, fallback) {
  return error?.errors?.[0]?.longMessage
    || error?.errors?.[0]?.message
    || error?.message
    || fallback;
}

function GoogleIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20">
      <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.24-.2-1.8H12v3.4h5.52a4.74 4.74 0 0 1-2.05 3.02v2.2h3.31c1.94-1.78 3.06-4.41 3.06-6.82Z" />
      <path fill="#34A853" d="M12 22c2.77 0 5.1-.91 6.78-2.48l-3.31-2.2c-.92.62-2.1.99-3.47.99-2.67 0-4.94-1.8-5.75-4.23H2.83v2.27A10.24 10.24 0 0 0 12 22Z" />
      <path fill="#FBBC05" d="M6.25 14.08A6.1 6.1 0 0 1 5.93 12c0-.72.12-1.42.32-2.08V7.65H2.83A10.02 10.02 0 0 0 1.75 12c0 1.57.38 3.05 1.08 4.35l3.42-2.27Z" />
      <path fill="#EA4335" d="M12 5.69c1.5 0 2.85.52 3.91 1.52l2.94-2.94C17.1 2.64 14.77 1.75 12 1.75a10.24 10.24 0 0 0-9.17 5.9l3.42 2.27C7.06 7.49 9.33 5.69 12 5.69Z" />
    </svg>
  );
}

function AuthModal({ mode, onClose, onSwitch }) {
  const { isLoaded: signInLoaded, signIn, setActive: setSignInActive } = useSignIn();
  const { isLoaded: signUpLoaded, signUp, setActive: setSignUpActive } = useSignUp();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState('form');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isSignUp = mode === 'sign-up';
  const isReady = isSignUp ? signUpLoaded : signInLoaded;

  async function handleGoogle() {
    setError('');
    if (!signInLoaded || !signIn) {
      setError('A autenticação ainda está carregando. Tente novamente.');
      return;
    }

    setLoading(true);
    try {
      await signIn.authenticateWithRedirect({
        strategy: 'oauth_google',
        redirectUrl: `${window.location.origin}/#/sso-callback`,
        redirectUrlComplete: `${window.location.origin}/#/`,
      });
    } catch (authError) {
      setError(getClerkError(authError, 'Não foi possível continuar com o Google.'));
      setLoading(false);
    }
  }

  async function handleCredentials(event) {
    event.preventDefault();
    setError('');

    if (!isReady) {
      setError('A autenticação ainda está carregando. Tente novamente.');
      return;
    }

    if (!email.trim() || !password) {
      setError('Informe o e-mail e a senha.');
      return;
    }

    if (isSignUp && password !== confirmPassword) {
      setError('As senhas não coincidem.');
      return;
    }

    setLoading(true);
    try {
      if (isSignUp) {
        await signUp.create({ emailAddress: email.trim(), password });
        await signUp.prepareEmailAddressVerification({ strategy: 'email_code' });
        setStep('verification');
      } else {
        const attempt = await signIn.create({ identifier: email.trim(), password });

        if (attempt.status === 'complete') {
          await setSignInActive({ session: attempt.createdSessionId });
          onClose();
          return;
        }

        if (attempt.status === 'needs_second_factor') {
          const emailFactor = attempt.supportedSecondFactors?.find(
            (factor) => factor.strategy === 'email_code',
          );

          if (!emailFactor) {
            throw new Error('Não foi possível confirmar este acesso neste dispositivo.');
          }

          await signIn.prepareSecondFactor({
            strategy: 'email_code',
            emailAddressId: emailFactor.emailAddressId,
          });
          setStep('second-factor');
        } else {
          throw new Error('O acesso exige uma etapa adicional não disponível.');
        }
      }
    } catch (authError) {
      setError(getClerkError(authError, isSignUp
        ? 'Não foi possível criar a conta.'
        : 'E-mail ou senha inválidos.'));
    } finally {
      setLoading(false);
    }
  }

  async function handleCode(event) {
    event.preventDefault();
    setError('');

    if (!code.trim()) {
      setError('Digite o código recebido por e-mail.');
      return;
    }

    setLoading(true);
    try {
      if (step === 'verification') {
        const attempt = await signUp.attemptEmailAddressVerification({ code: code.trim() });
        if (attempt.status !== 'complete') {
          throw new Error('A verificação ainda não foi concluída.');
        }
        await setSignUpActive({ session: attempt.createdSessionId });
      } else {
        const attempt = await signIn.attemptSecondFactor({
          strategy: 'email_code',
          code: code.trim(),
        });
        if (attempt.status !== 'complete') {
          throw new Error('A confirmação ainda não foi concluída.');
        }
        await setSignInActive({ session: attempt.createdSessionId });
      }
      onClose();
    } catch (authError) {
      setError(getClerkError(authError, 'Código inválido ou expirado.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="custom-auth-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="custom-auth-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button className="custom-auth-close" type="button" onClick={onClose} aria-label="Fechar">
          ×
        </button>

        {step === 'form' ? (
          <>
            <header className="custom-auth-header">
              <h1 id="auth-title">{isSignUp ? 'Criar sua conta' : 'Entrar no DomnAI'}</h1>
              <p>{isSignUp ? 'Preencha seus dados para começar.' : 'Acesse sua conta para continuar.'}</p>
            </header>

            <button className="google-auth-button" type="button" onClick={handleGoogle} disabled={loading}>
              <GoogleIcon />
              <span>Continuar com Google</span>
            </button>

            <div className="auth-divider"><span>ou</span></div>

            <form className="custom-auth-form" onSubmit={handleCredentials}>
              <label>
                <span>E-mail</span>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="Digite seu e-mail"
                  autoComplete="email"
                  inputMode="email"
                />
              </label>

              <label>
                <span>Senha</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Digite sua senha"
                  autoComplete={isSignUp ? 'new-password' : 'current-password'}
                />
              </label>

              {isSignUp ? (
                <label>
                  <span>Confirmar senha</span>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    placeholder="Digite a senha novamente"
                    autoComplete="new-password"
                  />
                </label>
              ) : null}

              <div id="clerk-captcha" />

              {error ? <p className="custom-auth-error" role="alert">{error}</p> : null}

              <button className="custom-auth-submit" type="submit" disabled={loading}>
                {loading ? 'Aguarde...' : isSignUp ? 'Criar conta' : 'Entrar'}
              </button>
            </form>

            <footer className="custom-auth-footer">
              <span>{isSignUp ? 'Já possui uma conta?' : 'Ainda não tem uma conta?'}</span>
              <button type="button" onClick={() => onSwitch(isSignUp ? 'sign-in' : 'sign-up')}>
                {isSignUp ? 'Fazer login' : 'Criar conta'}
              </button>
            </footer>
          </>
        ) : (
          <>
            <header className="custom-auth-header">
              <h1 id="auth-title">Confirme seu e-mail</h1>
              <p>Enviamos um código para <strong>{email}</strong>.</p>
            </header>

            <form className="custom-auth-form" onSubmit={handleCode}>
              <label>
                <span>Código de verificação</span>
                <input
                  type="text"
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="Digite o código"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                />
              </label>

              {error ? <p className="custom-auth-error" role="alert">{error}</p> : null}

              <button className="custom-auth-submit" type="submit" disabled={loading}>
                {loading ? 'Verificando...' : 'Confirmar acesso'}
              </button>

              <button className="custom-auth-back" type="button" onClick={() => setStep('form')}>
                Voltar
              </button>
            </form>
          </>
        )}
      </section>
    </div>
  );
}

function Landing() {
  const [authMode, setAuthMode] = useState(null);

  return (
    <main className="landing-page">
      <section className="landing-card" aria-label="Acesso ao DomnAI">
        <img
          className="official-logo"
          src={DOMNAI_LOGO}
          alt="DomnAI — Transforme escolhas em resultados com inteligência."
        />

        <div className="access-actions">
          <button className="primary-button" type="button" onClick={() => setAuthMode('sign-up')}>
            Criar conta
          </button>

          <button className="secondary-button" type="button" onClick={() => setAuthMode('sign-in')}>
            Fazer login
          </button>
        </div>
      </section>

      <FooterNavigation />

      {authMode ? (
        <AuthModal
          key={authMode}
          mode={authMode}
          onClose={() => setAuthMode(null)}
          onSwitch={setAuthMode}
        />
      ) : null}
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
      <Route path="/sso-callback" element={<AuthenticateWithRedirectCallback />} />
      <Route path="/login/*" element={<Navigate to="/" replace />} />
      <Route path="/cadastro/*" element={<Navigate to="/" replace />} />
      <Route path="/sobre" element={<InstitutionalPage page="sobre" />} />
      <Route path="/privacidade" element={<InstitutionalPage page="privacidade" />} />
      <Route path="/termos" element={<InstitutionalPage page="termos" />} />
      <Route path="/ajuda" element={<HelpPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
