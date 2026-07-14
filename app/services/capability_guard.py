import re
from collections.abc import Iterable


_EXTERNAL_URLS = re.compile(
    r"https?://(?:docs\.google\.com|drive\.google\.com|file\.io|dropbox\.com|bit\.ly|tinyurl\.com)/\S+",
    re.IGNORECASE,
)

_EMAIL_CLAIMS = re.compile(
    r"\b(?:já\s+)?(?:enviei|mandei|encaminhei|compartilhei)\b[^.\n]{0,140}"
    r"\b(?:por\s+)?(?:e-?mail|email)\b",
    re.IGNORECASE,
)

_ARTIFACT_CLAIMS = re.compile(
    r"\b(?:já\s+)?(?:criei|gerei|montei|preparei|exportei|disponibilizei)\b[^.\n]{0,160}"
    r"\b(?:planilha|arquivo|pdf|documento|link)\b",
    re.IGNORECASE,
)

_FUTURE_EXTERNAL_PROMISES = re.compile(
    r"\b(?:em\s+instantes|só\s+um\s+momento|aguarde|já\s+te\s+envio|vou\s+enviar|vou\s+mandar)\b"
    r"[^.\n]{0,180}\b(?:e-?mail|email|link|drive|dropbox|google\s+sheets)\b",
    re.IGNORECASE,
)


def _confirmed_set(confirmed_actions: Iterable[str] | None) -> set[str]:
    return {
        str(action or "").strip().casefold()
        for action in (confirmed_actions or [])
        if str(action or "").strip()
    }


def apply_capability_guard(
    text: str,
    confirmed_actions: Iterable[str] | None = None,
) -> str:
    """Bloqueia apenas alegações sem evidência técnica de execução.

    Confirmações esperadas das camadas executoras:
    - local_artifact_created: PDF, XLSX, CSV ou outro arquivo criado na plataforma.
    - external_link_generated: URL real devolvida por uma integração.
    - email_sent: envio confirmado pelo provedor de e-mail.
    """
    original = str(text or "").strip()
    if not original:
        return original

    confirmed = _confirmed_set(confirmed_actions)
    allow_local_artifact = "local_artifact_created" in confirmed
    allow_external_link = "external_link_generated" in confirmed
    allow_email = "email_sent" in confirmed

    sanitized = original
    blocked_reasons: list[str] = []

    if not allow_external_link:
        updated = _EXTERNAL_URLS.sub("", sanitized)
        if updated != sanitized:
            blocked_reasons.append("link externo não confirmado")
        sanitized = updated

    if not allow_email:
        updated = _EMAIL_CLAIMS.sub("", sanitized)
        if updated != sanitized:
            blocked_reasons.append("envio por e-mail não confirmado")
        sanitized = updated

        updated = _FUTURE_EXTERNAL_PROMISES.sub("", sanitized)
        if updated != sanitized:
            blocked_reasons.append("promessa de ação externa")
        sanitized = updated

    if not allow_local_artifact:
        updated = _ARTIFACT_CLAIMS.sub("", sanitized)
        if updated != sanitized:
            blocked_reasons.append("arquivo não confirmado")
        sanitized = updated

    lines = [line.rstrip() for line in sanitized.splitlines()]
    compact_lines: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        compact_lines.append(line)
        previous_blank = blank

    result = "\n".join(compact_lines).strip()
    if blocked_reasons:
        notice = (
            "Essa ação não teve confirmação técnica de execução. O DomnAI só informa que criou um "
            "arquivo, gerou um link ou realizou um envio depois que a ferramenta responsável devolver sucesso real."
        )
        result = f"{result}\n\n{notice}" if result else notice

    return result
