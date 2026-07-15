from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request


@dataclass(frozen=True)
class WebResearchResult:
    text: str
    sources: list[dict]


def should_research_web(message: str, operation: str | None = None) -> bool:
    text = f"{operation or ''} {message or ''}".casefold()
    explicit = (
        "pesquise", "pesquisa", "procure na internet", "busque na internet",
        "fontes", "referências", "referencias", "links oficiais", "notícias",
        "noticias", "atualizado", "atualizada", "hoje", "agora", "mais recente",
        "preço atual", "preco atual", "cotação", "cotacao", "concorrência",
        "concorrencia", "mercado atual", "lei atual", "regra atual",
    )
    operations = (
        "pesquisa de mercado", "concorrência", "concorrencia",
        "pesquisa e comparação", "cotação", "cotacao", "fornecedores",
        "tendências", "tendencias", "veículos", "veiculos", "viagens",
    )
    return any(marker in text for marker in explicit) or any(marker in text for marker in operations)


def _post(payload: dict) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada para pesquisa web.")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Pesquisa web recusada ({exc.code}): {detail[:500]}") from exc
    except error.URLError as exc:
        raise RuntimeError("Não foi possível conectar ao serviço de pesquisa web.") from exc
    except TimeoutError as exc:
        raise RuntimeError("A pesquisa web excedeu o limite de 8 segundos.") from exc


def _extract(data: dict) -> WebResearchResult:
    text = str(data.get("output_text") or "").strip()
    sources: list[dict] = []
    seen: set[str] = set()
    for output in data.get("output") or []:
        for content in output.get("content") or []:
            if content.get("type") == "output_text" and content.get("text") and not text:
                text = str(content.get("text") or "").strip()
            for annotation in content.get("annotations") or []:
                url = str(annotation.get("url") or annotation.get("source_url") or "").strip()
                title = str(annotation.get("title") or annotation.get("source_title") or url).strip()
                if url and url not in seen:
                    seen.add(url)
                    sources.append({"title": title[:240], "url": url[:1500]})
    if not text:
        raise RuntimeError("A pesquisa web não retornou conteúdo utilizável.")
    return WebResearchResult(text=text, sources=sources[:12])


def research_web(query: str) -> WebResearchResult:
    model = os.getenv("DOMNAI_WEB_SEARCH_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    instructions = (
        "Pesquise na web antes de responder. Use fontes atuais, confiáveis e diretamente relevantes. "
        "Diferencie fatos de inferências. Inclua referências verificáveis e não invente URLs. "
        "Responda em português do Brasil."
    )
    payload = {
        "model": model,
        "instructions": instructions,
        "input": query,
        "max_output_tokens": 1400,
        "tools": [{"type": "web_search"}],
    }
    return _extract(_post(payload))
