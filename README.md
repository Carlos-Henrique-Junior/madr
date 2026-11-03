# MADR — Meu Acervo Digital de Romances

API do projeto final do curso [FastAPI do Zero](https://fastapidozero.dunossauro.com/estavel/15/):
um acervo digital de livros e romancistas, com contas, autenticação JWT e CRUD.

## Stack

| Camada | Escolha |
|---|---|
| Linguagem | Python 3.13+ (imagem `python:3.13-slim`) |
| Framework | FastAPI |
| ORM | SQLAlchemy 2 async (`mapped_as_dataclass`) |
| Banco | PostgreSQL 17 em produção; SQLite async nos testes |
| Migrações | Alembic |
| Auth | JWT (`pyjwt`, HS256, 60 min, `sub` = email) + `pwdlib`/argon2 |
| Testes | pytest + pytest-asyncio + httpx (ASGI transport) — **98 testes**, 100% na API e 89% na web |
| Front-end | Jinja2 + HTMX servidos pelo próprio FastAPI (sem Node, sem build) |
| Container | Docker + Docker Compose |
| CI | GitHub Actions (testes em 3.13/3.14 + migrações contra Postgres) |

## Como rodar

### Com Docker (recomendado)

```bash
cp .env.example .env          # defina SECRET_KEY; sem ela o compose recusa subir
docker compose up --build
```

A API sobe em `http://localhost:8000` (porta do host configurável por `API_PORT`
no `.env`) e aplica `alembic upgrade head` no start.
Documentação interativa em `/docs`.

O container roda como usuário sem privilégios (`appuser`, uid 10001), tem
healthcheck em `/health`, reinicia sozinho (`unless-stopped`) e o Postgres só
publica a porta em `127.0.0.1:5432` — o banco não fica exposto na rede.
Verificação ponta a ponta (build, health, escrita real e persistência):

```bash
scripts/docker_check.sh
```

### Local

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install . pytest pytest-asyncio pytest-cov httpx freezegun ruff
cp .env.example .env
alembic upgrade head
uvicorn madr.app:app --reload
```

### Testes

```bash
pytest          # 98 testes; API com 100% de cobertura, web com 89%
ruff check .
```

## Interface web

A mesma aplicação serve uma interface Jinja2 + HTMX, sem Node e sem etapa de build:

| Rota | Descrição |
|---|---|
| `GET /login` / `POST /login` | formulário que grava o JWT em cookie `httpOnly` (`samesite=lax`) |
| `POST /sair` | apaga o cookie |
| `GET /painel` | métricas do acervo e últimos cadastros |
| `GET /livros` | lista com busca por título, filtro por ano e paginação de 20 |
| `GET /livros/tabela` | fragmento HTMX usado pela busca incremental e pelas exclusões |
| `GET /livros/novo`, `POST /livros` | cadastro de livro |
| `GET /livros/{id}/editar`, `POST /livros/{id}` | edição de livro |
| `GET /romancistas` + `/romancistas/tabela` | lista, busca e exclusão |
| `GET /romancistas/novo`, `POST /romancistas` | cadastro de romancista |
| `GET /romancistas/{id}/editar`, `POST /romancistas/{id}` | edição de romancista |

A API JSON continua em `/` e nos routers (`/conta`, `/livro`, `/romancista`, `/token`),
e o painel vive em `/painel` para não competir com a rota raiz da API. Os testes de
interface usam o mesmo banco SQLite em memória e o mesmo `client` dos testes da API.

## Endpoints

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/conta` | não | Cria conta (201) |
| PUT | `/conta/{id}` | sim | Atualiza a própria conta |
| DELETE | `/conta/{id}` | sim | Remove a própria conta |
| POST | `/token` | não | Login (form: `username`=email, `password`) |
| POST | `/refresh-token` | sim | Renova o access token |
| POST | `/livro` | sim | Cria livro (201) |
| GET | `/livro?titulo=&ano=&limit=&offset=` | não | Lista/filtra livros |
| GET | `/livro/{id}` | não | Detalhe do livro |
| PATCH | `/livro/{id}` | sim | Altera livro |
| DELETE | `/livro/{id}` | sim | Remove livro |
| POST | `/romancista` | sim | Cria romancista (201) |
| GET | `/romancista?nome=&limit=&offset=` | não | Lista/filtra romancistas |
| GET | `/romancista/{id}` | não | Detalhe da romancista |
| PATCH/PUT | `/romancista/{id}` | sim | Altera romancista |
| DELETE | `/romancista/{id}` | sim | Remove romancista (e seus livros) |

## Decisões

1. **Formato de erro único.** A spec pede `{"message": "..."}`; o FastAPI responde
   `{"detail": "..."}` por padrão. Um handler global converte toda `HTTPException`
   para `{"message": ...}`. Erros de validação seguem 422 do Pydantic.
2. **Divergência no login.** A seção “Erros de autenticação” pede
   `400 {"message": "Email ou senha incorretos"}`; um cenário Gherkin usa
   `detail: "Incorrect email or password"`. Prevaleceu o texto da spec, em português.
3. **POST /livro devolve 201.** O texto cita 200, o cenário Gherkin e a convenção
   REST pedem 201; mantive 201 (era o comportamento do curso).
4. **PATCH e PUT em `/romancista/{id}`.** A spec cita PATCH, o cenário usa PUT —
   as duas rotas existem e compartilham a mesma implementação.
5. **Sanitização** (`madr/sanitize.py`): decodifica entidades HTML (`&nbsp;`),
   troca pontuação por espaço, colapsa espaços, apara e converte para caixa baixa,
   preservando acentos. Aplicada em `titulo` e `nome` antes de qualquer escrita e
   também nos filtros de busca.
6. **Paginação** com `limit` (padrão 20, máx. 100) e `offset` (≥ 0) em todas as
   listagens; resposta no formato `{"livros": [...]}` / `{"romancistas": [...]}`.
7. **Romancista com livros** é apagada em cascata: o endpoint remove os livros antes
   (o SQLite só respeita `ON DELETE CASCADE` com PRAGMA ligado, então a remoção é
   explícita e determinística nos dois bancos).
8. **E-mail normalizado** para caixa baixa na criação/atualização de conta, para que
   unicidade e login não dependam da capitalização digitada.
