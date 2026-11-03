#!/usr/bin/env bash
# Verificação do container MADR: sobe com Postgres, exercita API + web e testa persistência.
set -uo pipefail
cd /home/lemosserver/madr

BASE=http://127.0.0.1:8000
STAMP=$(date +%s)
EMAIL="check$STAMP@example.com"
USER="check$STAMP"

wait_healthy() {
  local cid status=starting
  cid=$(docker compose ps -q api 2>/dev/null)
  for _ in $(seq 1 60); do
    [ -n "$cid" ] && status=$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null)
    [ "$status" = healthy ] && break
    sleep 2
  done
  echo "$status"
}

echo '### 1. build + subir'
docker compose up -d --build 2>&1 | tail -4

echo
echo "### 2. healthcheck: $(wait_healthy)"
docker compose ps

echo
echo '### 3. processo não é root'
docker compose exec -T api id

echo
echo '### 4. migração aplicada'
docker compose exec -T api alembic current 2>&1 | tail -1

echo
echo '### 5. rotas'
for path in / /health /docs /login; do
  curl -s -o /dev/null -w "$path %{http_code}\n" "$BASE$path"
done

echo
echo '### 6. escrita real (conta -> token -> romancista -> livro)'
curl -s -w '\nHTTP %{http_code}\n' -X POST "$BASE/conta" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"email\":\"$EMAIL\",\"senha\":\"senha-segura-123\"}"
JWT=$(curl -s -X POST "$BASE/token" \
  -d "username=$EMAIL&password=senha-segura-123" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
ROMANCISTA=$(curl -s -X POST "$BASE/romancista" \
  --oauth2-bearer "$JWT" -H 'Content-Type: application/json' \
  -d "{\"nome\":\"Check $STAMP\"}")
echo "$ROMANCISTA"
RID=$(echo "$ROMANCISTA" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
curl -s -w '\nHTTP %{http_code}\n' -X POST "$BASE/livro" \
  --oauth2-bearer "$JWT" -H 'Content-Type: application/json' \
  -d "{\"ano\":1977,\"titulo\":\"Livro $STAMP\",\"romancista_id\":$RID}"

echo
echo '### 7. persistência após restart'
docker compose restart 2>&1 | tail -2
echo "health: $(wait_healthy)"
curl -s "$BASE/livro?limit=5"; echo

echo
echo '### 8. dados no Postgres'
docker compose exec -T db psql -U madr -d madr -c \
  'select (select count(*) from romancistas) as romancistas, (select count(*) from livros) as livros;'

echo
echo '### 9. derrubar (volume preservado)'
docker compose down 2>&1 | tail -2
