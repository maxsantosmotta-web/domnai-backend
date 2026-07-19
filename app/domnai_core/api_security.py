from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Iterable, Protocol


class AuthenticationError(PermissionError):
    pass


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class ApiPrincipal:
    subject: str
    scopes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError("ApiPrincipal.subject não pode ser vazio.")

    def require(self, scope: str) -> None:
        normalized = scope.strip().lower()
        if normalized not in self.scopes:
            raise AuthorizationError(f"Escopo obrigatório ausente: {normalized}")


class TokenAuthenticator(Protocol):
    def authenticate(self, token: str) -> ApiPrincipal:
        ...


class StaticBearerAuthenticator:
    """Autenticador interno simples, constante no tempo e substituível.

    Serve apenas para a API paralela protegida. Não substitui Clerk nem é montado
    automaticamente na aplicação externa.
    """

    def __init__(self, *, token: str, subject: str = "internal", scopes: Iterable[str] = ()) -> None:
        normalized_token = token.strip()
        if not normalized_token:
            raise ValueError("O token interno não pode ser vazio.")
        self._digest = hashlib.sha256(normalized_token.encode("utf-8")).digest()
        self._principal = ApiPrincipal(
            subject=subject.strip() or "internal",
            scopes=tuple(dict.fromkeys(value.strip().lower() for value in scopes if value.strip())),
        )

    def authenticate(self, token: str) -> ApiPrincipal:
        candidate = hashlib.sha256(token.strip().encode("utf-8")).digest()
        if not token.strip() or not hmac.compare_digest(candidate, self._digest):
            raise AuthenticationError("Credencial inválida.")
        return self._principal


def extract_bearer_token(authorization: str | None) -> str:
    value = str(authorization or "").strip()
    if not value:
        raise AuthenticationError("Credencial ausente.")
    scheme, separator, token = value.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationError("Use Authorization: Bearer <token>.")
    return token.strip()
