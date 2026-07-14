import re


_PROHIBITED_URLS = re.compile(
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


def apply_capability_guard(text: str) -> str:
    """Remove afirmações de ações externas que o DomnAI não executou de fato."""
    original = str(text or "").strip()
    if not original:
        return original

    sanitized = _PROHIBITED_URLS.sub("", original)
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
            "Não consigo criar ou compartilhar Google Sheets, enviar e-mails ou gerar links externos "
            "sem uma integração ativa. Posso entregar o conteúdo diretamente nesta conversa ou em "
            "um arquivo realmente gerado pelo DomnAI."
        )
        result = f"{result}\n\n{notice}" if result else notice
    return result
