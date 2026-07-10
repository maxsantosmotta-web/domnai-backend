import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "DomnAI")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str | None = os.getenv("DATABASE_URL")
    clerk_publishable_key: str | None = os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
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
