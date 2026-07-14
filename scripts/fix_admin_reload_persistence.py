from pathlib import Path

TARGET = Path("/frontend/src/AdminAccessBoundary.jsx")

old_clear = """  useEffect(() => {
    if (!isSignedIn && !isSigningOut) sessionStorage.removeItem(ADMIN_ENTRY_KEY);
  }, [isSignedIn, isSigningOut]);
"""

new_clear = """  useEffect(() => {
    if (isLoaded && !isSignedIn && !isSigningOut) sessionStorage.removeItem(ADMIN_ENTRY_KEY);
  }, [isLoaded, isSignedIn, isSigningOut]);
"""

old_redirect = """  useEffect(() => {
    if (!adminRoute || isSigningOut) return;
    if (!adminRequested || (userLoaded && !isOwnerCandidate)) {
      sessionStorage.removeItem(ADMIN_ENTRY_KEY);
      navigateTo('/');
    }
  }, [adminRequested, adminRoute, isOwnerCandidate, isSigningOut, userLoaded]);
"""

new_redirect = """  useEffect(() => {
    if (!adminRoute || isSigningOut || !isLoaded || !userLoaded) return;
    if (!adminRequested || !isOwnerCandidate) {
      sessionStorage.removeItem(ADMIN_ENTRY_KEY);
      navigateTo('/');
    }
  }, [adminRequested, adminRoute, isLoaded, isOwnerCandidate, isSigningOut, userLoaded]);
"""

source = TARGET.read_text(encoding="utf-8")

if source.count(old_clear) != 1:
    raise SystemExit("Trecho de limpeza administrativa não encontrado exatamente uma vez.")
if source.count(old_redirect) != 1:
    raise SystemExit("Trecho de redirecionamento administrativo não encontrado exatamente uma vez.")

source = source.replace(old_clear, new_clear, 1)
source = source.replace(old_redirect, new_redirect, 1)
TARGET.write_text(source, encoding="utf-8")

print("Persistência do Painel Adm protegida durante carregamento do Clerk.")
