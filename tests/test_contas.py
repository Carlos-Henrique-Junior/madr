from http import HTTPStatus

import pytest
from sqlalchemy import select

from madr.models import User


async def test_criar_conta(client):
    resposta = await client.post(
        '/conta',
        json={
            'username': 'dunossauro',
            'email': 'dudu@dudu.com',
            'senha': '1234567',
        },
    )
    assert resposta.status_code == HTTPStatus.CREATED
    assert resposta.json() == {
        'id': 1,
        'email': 'dudu@dudu.com',
        'username': 'dunossauro',
    }


async def test_criar_conta_duplicada(client, usuario):
    resposta = await client.post(
        '/conta',
        json={
            'username': 'dunossauro',
            'email': 'dudu@dudu.com',
            'senha': '1234567',
        },
    )
    assert resposta.status_code == HTTPStatus.CONFLICT
    assert resposta.json() == {'message': 'Conta já consta no MADR'}


async def test_senha_nao_aparece_e_e_hasheada(client, session):
    await client.post(
        '/conta',
        json={
            'username': 'dunossauro',
            'email': 'dudu@dudu.com',
            'senha': '1234567',
        },
    )
    resposta = await client.post(
        '/token', data={'username': 'dudu@dudu.com', 'password': '1234567'}
    )
    assert resposta.status_code == HTTPStatus.OK

    user = await session.scalar(select(User))
    assert user.senha != '1234567'


async def test_login_inexistente(client):
    resposta = await client.post(
        '/token', data={'username': 'ninguem@nada.com', 'password': 'x'}
    )
    assert resposta.status_code == HTTPStatus.BAD_REQUEST
    assert resposta.json() == {'message': 'Email ou senha incorretos'}


async def test_login_senha_errada(client, usuario):
    resposta = await client.post(
        '/token', data={'username': usuario.email, 'password': 'errada'}
    )
    assert resposta.status_code == HTTPStatus.BAD_REQUEST
    assert resposta.json() == {'message': 'Email ou senha incorretos'}


async def test_login_com_sucesso(client, usuario):
    resposta = await client.post(
        '/token', data={'username': usuario.email, 'password': '1234567'}
    )
    assert resposta.status_code == HTTPStatus.OK
    corpo = resposta.json()
    assert corpo['token_type'] == 'bearer'
    assert corpo['access_token']


async def test_atualizar_conta(client, usuario, headers):
    resposta = await client.put(
        f'/conta/{usuario.id}',
        json={
            'username': 'outro',
            'email': 'outro@exemplo.com',
            'senha': '7654321',
        },
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {
        'id': usuario.id,
        'email': 'outro@exemplo.com',
        'username': 'outro',
    }


async def test_atualizar_conta_de_outro_usuario(
    client, usuario, headers, session
):
    outro = User(
        username='outro',
        email='outro@exemplo.com',
        senha='hash',
    )
    session.add(outro)
    await session.commit()
    await session.refresh(outro)

    resposta = await client.put(
        f'/conta/{outro.id}',
        json={
            'username': 'xyz',
            'email': 'xyz@exemplo.com',
            'senha': '1234567',
        },
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED
    assert resposta.json() == {'message': 'Não autorizado'}


async def test_atualizar_conta_sem_token(client, usuario):
    resposta = await client.put(
        f'/conta/{usuario.id}',
        json={
            'username': 'outro',
            'email': 'outro@exemplo.com',
            'senha': '1234567',
        },
    )
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


async def test_atualizar_conta_com_conflito(client, headers, usuario):
    await client.post(
        '/conta',
        json={
            'username': 'outro',
            'email': 'outro@exemplo.com',
            'senha': '1234567',
        },
    )
    resposta = await client.put(
        f'/conta/{usuario.id}',
        json={
            'username': 'outro',
            'email': 'outro@exemplo.com',
            'senha': '1234567',
        },
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.CONFLICT


async def test_refresh_token(client, headers):
    resposta = await client.post('/refresh-token', headers=headers)
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json()['token_type'] == 'bearer'


async def test_refresh_token_sem_autenticacao(client):
    resposta = await client.post('/refresh-token')
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED
    assert resposta.json() == {'message': 'Não autorizado'}


async def test_token_invalido(client):
    resposta = await client.post(
        '/refresh-token', headers={'Authorization': 'Bearer nao-e-um-jwt'}
    )
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


async def test_deletar_conta(client, usuario, headers):
    resposta = await client.delete(f'/conta/{usuario.id}', headers=headers)
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {'message': 'Conta deletada com sucesso'}


async def test_deletar_conta_de_outro(client, usuario, headers, session):
    outro = User(username='outro', email='outro@exemplo.com', senha='hash')
    session.add(outro)
    await session.commit()
    await session.refresh(outro)

    resposta = await client.delete(f'/conta/{outro.id}', headers=headers)
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


async def test_deletar_conta_sem_token(client, usuario):
    resposta = await client.delete(f'/conta/{usuario.id}')
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize(
    'payload',
    [
        {'username': 'ab', 'email': 'a@b.com', 'senha': '1234567'},
        {'username': 'abc', 'email': 'nao-e-email', 'senha': '1234567'},
        {'username': 'abc', 'email': 'a@b.com', 'senha': '123'},
    ],
)
async def test_conta_invalida(client, payload):
    resposta = await client.post('/conta', json=payload)
    assert resposta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
