from pathlib import Path

path = Path('/frontend/src/App.jsx')
source = path.read_text(encoding='utf-8')

old = '''function Home() {
  const { isLoaded, isSignedIn } = useAuth();

  if (isLoaded && isSignedIn) {
    return <Dashboard />;
  }

  return <Landing />;
}'''

new = '''function Home() {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return <div aria-hidden="true" style={{ minHeight: '100vh', background: '#000' }} />;
  }

  if (isSignedIn) {
    return <Dashboard />;
  }

  return <Landing />;
}'''

if old not in source:
    raise RuntimeError('Não foi possível localizar o estado inicial de autenticação em App.jsx.')

source = source.replace(old, new, 1)
path.write_text(source, encoding='utf-8')
