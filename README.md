# DomnAI

Plataforma de apoio à decisão.

**Slogan:** Transforme escolhas em resultados com inteligência.

## Proposta

O DomnAI ajuda pessoas a pesquisar, analisar, comparar e tomar decisões melhores antes de agir. O sistema atende operações como análise contratual, comparação de produtos, avaliação de orçamentos, negociação, abertura e diagnóstico de empresas, finanças, investimentos, veículos, imóveis e cálculo de rescisão trabalhista.

## Arquitetura atual

- Backend Python com FastAPI e Uvicorn.
- Frontend React com Vite.
- Autenticação com Clerk.
- PostgreSQL com SQLAlchemy.
- Migrações versionadas com Alembic.
- Faturamento e créditos com Stripe.
- Biblioteca e lixeira por usuário.
- Memória de conversa e memória estruturada de diagnóstico.
- Orquestrador universal para interpretar intenção e selecionar o fluxo correto.
- Refinador final para melhorar clareza sem alterar evidências ou resultados determinísticos.
- Motor determinístico de cálculo de rescisão trabalhista.
- Geração real de relatórios PDF com confirmação explícita do usuário.

## Fluxo de inteligência

Toda operação entra pelo mesmo fluxo:

1. autenticação e validação de crédito;
2. carregamento do histórico, anexos e memória estruturada;
3. planejamento pelo Orquestrador;
4. seleção de motor especializado, quando disponível;
5. geração da resposta-base;
6. refinamento final;
7. atualização da memória;
8. medição e cobrança de créditos;
9. entrega ao frontend.

O motor especializado atualmente cadastrado é `labor_termination`, usado em cálculos de rescisão trabalhista. As demais operações usam o motor geral, sempre com Orquestração e Refinamento.

## PDF

A oferta de PDF só pode aparecer quando a operação estiver concluída e não houver informação essencial pendente. O arquivo nunca é criado automaticamente.

Após confirmação explícita do usuário, o frontend chama:

```text
POST /api/reports/pdf
```

O relatório pode conter resumo, seções, indicadores, tabelas e gráficos sustentados pelos dados. Depois de criado, é salvo na Biblioteca do próprio usuário.

## Banco de dados e migrações

O banco usa Alembic. Na produção, o container executa automaticamente:

```bash
alembic upgrade head
```

antes de iniciar o servidor.

Para criar uma nova migração localmente:

```bash
alembic revision --autogenerate -m "descricao da alteracao"
alembic upgrade head
```

Não adicionar ou alterar tabelas apenas com `Base.metadata.create_all`. Mudanças de estrutura devem receber uma nova revisão em `migrations/versions`.

## Rodar localmente

Backend:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Variáveis principais:

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `DOMNAI_OPENAI_MODEL`
- `DOMNAI_ORCHESTRATOR_MODEL`
- `DOMNAI_REFINER_MODEL`
- `CLERK_PUBLISHABLE_KEY` ou equivalente suportada
- `CLERK_SECRET_KEY`
- `CLERK_AUTHORIZED_PARTIES`
- `STRIPE_SECRET_KEY`

## Endpoints principais

- `GET /health`
- `POST /api/chat/respond`
- `GET|PUT /api/chat-state`
- `GET|POST /api/library`
- `GET /api/library/{id}/content`
- `POST /api/library/{id}/trash`
- `GET|DELETE /api/trash`
- `POST /api/trash/{id}/restore`
- `DELETE /api/trash/{id}`
- `POST /api/reports/pdf`
- rotas de perfil, autenticação, faturamento e decisões

As rotas de diagnóstico e inicialização de banco exigem autenticação. `/api/database/init` aceita somente `POST`.

## Health check

`GET /health` informa o estado do backend e verifica:

- conexão real com PostgreSQL;
- configuração da OpenAI;
- configuração do Clerk;
- configuração do Stripe;
- disponibilidade do gerador de PDF.

O status pode ser `ok` ou `degraded`.

## Deploy

O Railway usa o `Dockerfile` da raiz. O build compila o frontend, instala as dependências do backend, executa as migrações e inicia o FastAPI na porta fornecida pelo ambiente.

## Estado atual

O DomnAI já possui autenticação, banco, pagamentos, créditos, IA real, memória, biblioteca, lixeira, Orquestrador, Refinador, motor trabalhista determinístico e geração de PDF. A etapa final é a validação completa em produção e a expansão gradual de motores especializados.
