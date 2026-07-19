from __future__ import annotations

from typing import Callable

from fastapi import HTTPException

from app.auth import verify_clerk_token
from app.domnai_core.api_security import ApiPrincipal, AuthenticationError


class ClerkTokenAuthenticator:
    """Adapta a identidade Clerk existente ao contrato da API paralela."""

    def __init__(
        self,
        *,
        scopes: tuple[str, ...],
        verifier: Callable[[str], dict] = verify_clerk_token,
    ) -> None:
        self._scopes = tuple(dict.fromkeys(value.strip().lower() for value in scopes if value.strip()))
        if not self._scopes:
            raise ValueError("ClerkTokenAuthenticator exige ao menos um escopo.")
        self._verifier = verifier

    def authenticate(self, token: str) -> ApiPrincipal:
        if not token.strip():
            raise AuthenticationError("Credencial ausente.")
        try:
            payload = self._verifier(token.strip())
        except HTTPException as exc:
            raise AuthenticationError("Sessão inválida ou expirada.") from exc
        except Exception as exc:
            raise AuthenticationError("Não foi possível validar a sessão.") from exc
        subject = str(payload.get("sub") or "").strip()
        if not subject:
            raise AuthenticationError("Sessão sem usuário identificado.")
        return ApiPrincipal(subject=subject, scopes=self._scopes)
