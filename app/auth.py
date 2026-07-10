import base64
from functools import lru_cache
from typing import Any
from urllib.request import urlopen

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from app.config import settings


def _decode_clerk_domain(publishable_key: str) -> str:
    try:
        encoded = publishable_key.split("_", 2)[2]
        encoded += "=" * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(encoded).decode("utf-8").rstrip("$")
    except (IndexError, ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY inválida.") from exc

    if not decoded:
        raise RuntimeError("Não foi possível identificar o domínio da instância Clerk.")

    return decoded


@lru_cache(maxsize=1)
def get_clerk_issuer() -> str:
    if not settings.clerk_publishable_key:
        raise RuntimeError("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY não configurada.")

    return f"https://{_decode_clerk_domain(settings.clerk_publishable_key)}"


@lru_cache(maxsize=1)
def get_jwk_client() -> PyJWKClient:
    issuer = get_clerk_issuer()
    return PyJWKClient(f"{issuer}/.well-known/jwks.json")


def verify_clerk_token(token: str) -> dict[str, Any]:
    try:
        signing_key = get_jwk_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=get_clerk_issuer(),
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    authorized_party = payload.get("azp")
    if settings.clerk_authorized_parties and authorized_party not in settings.clerk_authorized_parties:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Origem da sessão não autorizada.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def require_authenticated_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_clerk_token(authorization.removeprefix("Bearer ").strip())
