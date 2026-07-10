import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


def _first_env(*names: str) -> tuple[str | None, str | None]:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip(), name
    return None, None


_clerk_publishable_key, _clerk_publishable_key_source = _first_env(
    "CLERK_PUBLISHABLE_KEY",
    "VITE_CLERK_PUBLISHABLE_KEY",
    "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "DomnAI")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str | None = os.getenv("DATABASE_URL")
    clerk_publishable_key: str | None = _clerk_publishable_key
    clerk_publishable_key_source: str | None = _clerk_publishable_key_source
    clerk_secret_key: str | None = os.getenv("CLERK_SECRET_KEY")
    clerk_authorized_parties: tuple[str, ...] = field(
        default_factory=lambda: _parse_csv(
            os.getenv(
                "CLERK_AUTHORIZED_PARTIES",
                "https://domnai.iattomassist.com.br,http://localhost:3000,http://localhost:5173",
            )
        )
    )


settings = Settings()
