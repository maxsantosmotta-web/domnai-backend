import re


_EXTERNAL_URLS = re.compile(
    r"https?://(?:docs\.google\.com|drive\.google\.com|file\.io|dropbox\.com|bit\.ly|tinyurl\.com)/\S+",
    re.IGNORECASE,
)

_EXTERNAL_ACTION_CLAIMS = re.compile(
    r"\b(?:já\s+)?(?:criei|gerei|configurei|compartilhei|enviei|mandei)\b[^.\n]{0,120}"
    r"\b(?:google\s+sheets|planilha|e-?mail|email|link|drive|dropbox)\b",
    re.IGNORECASE,
)

_FUTURE_PROMISES = re.compile(
    r"\b(?:em\s+instantes|só\s+um\s+momento|aguarde|já\s+te\s+envio|vou\s+enviar|vou\s+criar)\b[^.\n]{0,160}",
    re.IGNORECASE,
)


def apply_capability_guard(
    text: str,
    confirmed_actions: set[str] | None = None,
) -> str:
    """Bloqueia apenas ações externas não confirmadas por uma integração real.

    Integrações futuras devem informar ações confirmadas, por exemplo:
    - ``google_sheets_created``
    - ``email_sent``
    - ``external_link_generated``
    """
    original = str(text or "").strip()
    if not original:
        return original

    confirmed = confirmed_actions or set()
    allow_sheets = "google_sheets_created" in confirmed
    allow_email = "email_sent" in confirmed
    allow_link = "external_link_generated" in confirmed

    sanitized = original
    if not allow_link:
        sanitized = _EXTERNAL_URLS.sub("", sanitized)

    if not (allow_sheets and allow_email and allow_link):
        sanitized = _EXTERNAL_ACTION_CLAIMS.sub("", sanitized)
        sanitized = _FUTURE_PROMISES.sub("", sanitized)

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
    changed = result != original
    if changed:
        notice = (
            "Essa ação só pode ser confirmada quando a integração correspondente executar e retornar "
            "sucesso. Sem essa confirmação, entrego o conteúdo diretamente nesta conversa ou em um "
            "arquivo realmente gerado pelo DomnAI."
        )
        result = f"{result}\n\n{notice}" if result else notice
    return result
