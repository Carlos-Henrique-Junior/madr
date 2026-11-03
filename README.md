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
| Testes | pytest + pytest-asyncio + httpx (ASGI transport) — **66 testes, 100% de cobertura** |
| Container | Docker + Docker Compose |
| CI | GitHub Actions (testes em 3.13/3.14 + migrações contra Postgres) |

## Como rodar

### Com Docker (recomendado)

```bash
cp .env.example .env          # ajuste SECRET_KEY
docker compose up --build
```

A API sobe em `http://localhost:8000` e aplica `alembic upgrade head` no start.
Documentação interativa em `/docs`.

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
pytest          # 66 testes, cobertura 100%
ruff check .
```

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
