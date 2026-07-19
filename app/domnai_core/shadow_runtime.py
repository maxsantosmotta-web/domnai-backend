from __future__ import annotations

import logging
import threading
from functools import lru_cache

from app.domnai_core.shadow_results import PersistingShadowComparisonSink, PostgresShadowResultStore
from app.domnai_core.shadow_validation import ShadowValidationSettings, ShadowValidator

logger = logging.getLogger("domnai.shadow_runtime")


@lru_cache(maxsize=1)
def get_shadow_store() -> PostgresShadowResultStore:
    store = PostgresShadowResultStore()
    store.ensure_schema()
    return store


def schedule_persisted_shadow_validation(
    *,
    request_id: str,
    user_id: str,
    conversation_id: str,
    message: str,
    operation: str | None,
    history: list[dict],
    legacy_text: str,
    legacy_provider: str,
) -> bool:
    """Executa o candidato em segundo plano e persiste somente métricas seguras."""
    try:
        settings = ShadowValidationSettings.from_env()
    except Exception:
        logger.exception("Configuração inválida de shadow validation; execução ignorada.")
        return False
    if not settings.selects(f"{user_id}:{request_id}"):
        return False

    def target() -> None:
        try:
            store = get_shadow_store()
            validator = ShadowValidator(settings, sink=PersistingShadowComparisonSink(store))
            validator.run(
                request_id=request_id,
                user_id=user_id,
                conversation_id=conversation_id,
                message=message,
                operation=operation,
                history=history,
                legacy_text=legacy_text,
                legacy_provider=legacy_provider,
            )
        except Exception:
            logger.exception("Falha isolada ao persistir validação shadow.")

    threading.Thread(
        target=target,
        name=f"domnai-shadow-persist-{request_id[:8]}",
        daemon=True,
    ).start()
    return True
