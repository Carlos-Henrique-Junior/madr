from datetime import UTC, datetime, timedelta

import jwt as pyjwt

from madr.database import get_session
from madr.settings import Settings

settings = Settings()


def _token(payload: dict) -> str:
    return pyjwt.encode(
        payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def _headers(token: str) -> dict:
    return {'Authorization': f'Bearer {token}'}


async def test_token_sem_subject(client):
    token = _token({'exp': datetime.now(UTC) + timedelta(minutes=5)})
    resposta = await client.post('/refresh-token', headers=_headers(token))
    assert resposta.status_code == 401
    assert resposta.json() == {'message': 'Não autorizado'}


async def test_token_expirado(client):
    token = _token(
        {
            'sub': 'dudu@dudu.com',
            'exp': datetime.now(UTC) - timedelta(minutes=1),
        }
    )
    resposta = await client.post('/refresh-token', headers=_headers(token))
    assert resposta.status_code == 401


async def test_token_de_usuario_inexistente(client):
    token = _token(
        {
            'sub': 'fantasma@madr.com',
            'exp': datetime.now(UTC) + timedelta(minutes=5),
        }
    )
    resposta = await client.post('/refresh-token', headers=_headers(token))
    assert resposta.status_code == 401


async def test_get_session_entrega_uma_sessao():
    gerador = get_session()
    sessao = await gerador.__anext__()
    assert sessao is not None
    await gerador.aclose()
