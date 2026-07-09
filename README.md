# DomnAI Backend

Backend oficial do DomnAI.

**Slogan:** Transforme escolhas em resultados com inteligência.

## Proposta

DomnAI é uma plataforma de apoio à decisão, criada para ajudar pessoas a pesquisar, analisar, comparar e tomar decisões melhores antes de agir.

O MVP foca em análises em texto para casos como:

- análise de contratos;
- comparação de produtos;
- avaliação de orçamentos;
- negociação de preços;
- abertura de empresas;
- outras decisões importantes do dia a dia.

## Stack inicial

- Python
- FastAPI
- Uvicorn

## Rodar localmente

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints iniciais

- `GET /`
- `GET /health`
- `GET /api/decisions/categories`
- `POST /api/decisions/analyze`

## Status

Fase 2 — Backend inicial.

Ainda sem banco, sem autenticação, sem pagamentos e sem IA real.
