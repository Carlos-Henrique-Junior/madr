from http import HTTPStatus

from madr.models import Romancista


async def test_criar_romancista(client, headers):
    resposta = await client.post(
        '/romancista', json={'nome': 'Clarice Lispector'}, headers=headers
    )
    assert resposta.status_code == HTTPStatus.CREATED
    assert resposta.json() == {'id': 1, 'nome': 'clarice lispector'}


async def test_criar_romancista_sem_token(client):
    resposta = await client.post('/romancista', json={'nome': 'Clarice'})
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED
    assert resposta.json() == {'message': 'Não autorizado'}


async def test_criar_romancista_duplicada(client, headers, romancista):
    resposta = await client.post(
        '/romancista', json={'nome': 'Clarice Lispector'}, headers=headers
    )
    assert resposta.status_code == HTTPStatus.CONFLICT
    assert resposta.json() == {'message': 'Romancista já consta no MADR'}


async def test_ler_romancista(client, romancista):
    resposta = await client.get(f'/romancista/{romancista.id}')
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {
        'id': romancista.id,
        'nome': 'clarice lispector',
    }


async def test_ler_romancista_inexistente(client):
    resposta = await client.get('/romancista/99')
    assert resposta.status_code == HTTPStatus.NOT_FOUND
    assert resposta.json() == {'message': 'Romancista não consta no MADR'}


async def test_atualizar_romancista_patch(client, headers, romancista):
    resposta = await client.patch(
        f'/romancista/{romancista.id}',
        json={'nome': 'Manuel Bandeira'},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {
        'id': romancista.id,
        'nome': 'manuel bandeira',
    }


async def test_atualizar_romancista_put(client, headers, romancista):
    resposta = await client.put(
        f'/romancista/{romancista.id}',
        json={'nome': 'Machado de Assis'},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json()['nome'] == 'machado de assis'


async def test_atualizar_romancista_inexistente(client, headers):
    resposta = await client.patch(
        '/romancista/99', json={'nome': 'x'}, headers=headers
    )
    assert resposta.status_code == HTTPStatus.NOT_FOUND


async def test_atualizar_romancista_sem_token(client, romancista):
    resposta = await client.patch(
        f'/romancista/{romancista.id}', json={'nome': 'x'}
    )
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


async def test_atualizar_romancista_com_conflito(
    client, headers, session, romancista
):
    outra = Romancista(nome='outra romancista')
    session.add(outra)
    await session.commit()

    resposta = await client.patch(
        f'/romancista/{outra.id}',
        json={'nome': 'Clarice Lispector'},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.CONFLICT


async def test_deletar_romancista(client, headers, romancista):
    resposta = await client.delete(
        f'/romancista/{romancista.id}', headers=headers
    )
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {'message': 'Romancista deletada no MADR'}


async def test_deletar_romancista_inexistente(client, headers):
    resposta = await client.delete('/romancista/99', headers=headers)
    assert resposta.status_code == HTTPStatus.NOT_FOUND


async def test_deletar_romancista_sem_token(client, romancista):
    resposta = await client.delete(f'/romancista/{romancista.id}')
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


async def test_deletar_romancista_apaga_livros(
    client, headers, session, romancista, livro
):
    resposta = await client.delete(
        f'/romancista/{romancista.id}', headers=headers
    )
    assert resposta.status_code == HTTPStatus.OK
    assert (await client.get(f'/livro/{livro.id}')).status_code == 404


async def test_filtro_de_romancistas(client, headers):
    for nome in ['Clarice Lispector', 'Manuel Bandeira', 'Paulo Leminski']:
        await client.post('/romancista', json={'nome': nome}, headers=headers)

    resposta = await client.get('/romancista', params={'nome': 'a'})
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {
        'romancistas': [
            {'id': 1, 'nome': 'clarice lispector'},
            {'id': 2, 'nome': 'manuel bandeira'},
            {'id': 3, 'nome': 'paulo leminski'},
        ]
    }


async def test_filtro_de_romancistas_sem_resultado(client):
    resposta = await client.get('/romancista', params={'nome': 'zzz'})
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {'romancistas': []}


async def test_listar_romancistas_sem_filtro(client, romancista):
    resposta = await client.get('/romancista')
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {
        'romancistas': [{'id': romancista.id, 'nome': 'clarice lispector'}]
    }


async def test_raiz(client):
    resposta = await client.get('/')
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {'message': 'Bem-vindo ao MADR'}
