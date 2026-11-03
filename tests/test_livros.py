from http import HTTPStatus

from madr.models import Livro, Romancista

PAYLOAD = {'ano': 1973, 'titulo': 'Café Da Manhã Dos Campeões'}


async def test_criar_livro(client, headers, romancista):
    resposta = await client.post(
        '/livro',
        json={**PAYLOAD, 'romancista_id': romancista.id},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.CREATED
    assert resposta.json() == {
        'id': 1,
        'ano': 1973,
        'titulo': 'café da manhã dos campeões',
        'romancista_id': romancista.id,
    }


async def test_criar_livro_sem_token(client, romancista):
    resposta = await client.post(
        '/livro', json={**PAYLOAD, 'romancista_id': romancista.id}
    )
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED
    assert resposta.json() == {'message': 'Não autorizado'}


async def test_criar_livro_romancista_inexistente(client, headers):
    resposta = await client.post(
        '/livro', json={**PAYLOAD, 'romancista_id': 99}, headers=headers
    )
    assert resposta.status_code == HTTPStatus.NOT_FOUND
    assert resposta.json() == {'message': 'Romancista não consta no MADR'}


async def test_criar_livro_duplicado(client, headers, romancista, livro):
    resposta = await client.post(
        '/livro',
        json={**PAYLOAD, 'romancista_id': romancista.id},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.CONFLICT
    assert resposta.json() == {'message': 'Livro já consta no MADR'}


async def test_ler_livro(client, livro):
    resposta = await client.get(f'/livro/{livro.id}')
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json()['titulo'] == 'café da manhã dos campeões'


async def test_ler_livro_inexistente(client):
    resposta = await client.get('/livro/99')
    assert resposta.status_code == HTTPStatus.NOT_FOUND
    assert resposta.json() == {'message': 'Livro não consta no MADR'}


async def test_atualizar_livro(client, headers, livro):
    resposta = await client.patch(
        f'/livro/{livro.id}', json={'ano': 1974}, headers=headers
    )
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {
        'id': livro.id,
        'ano': 1974,
        'titulo': 'café da manhã dos campeões',
        'romancista_id': livro.romancista_id,
    }


async def test_atualizar_livro_com_novo_titulo(client, headers, livro):
    resposta = await client.patch(
        f'/livro/{livro.id}',
        json={'titulo': 'Grande Sertão: Veredas'},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json()['titulo'] == 'grande sertão veredas'


async def test_atualizar_livro_inexistente(client, headers):
    resposta = await client.patch(
        '/livro/99', json={'ano': 1974}, headers=headers
    )
    assert resposta.status_code == HTTPStatus.NOT_FOUND


async def test_atualizar_livro_sem_token(client, livro):
    resposta = await client.patch(f'/livro/{livro.id}', json={'ano': 1974})
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


async def test_atualizar_livro_para_titulo_existente(
    client, headers, session, romancista, livro
):
    outro = Livro(ano=2000, titulo='outro livro', romancista_id=romancista.id)
    session.add(outro)
    await session.commit()

    resposta = await client.patch(
        f'/livro/{outro.id}',
        json={'titulo': 'café da manhã dos campeões'},
        headers=headers,
    )
    assert resposta.status_code == HTTPStatus.CONFLICT


async def test_deletar_livro(client, headers, livro):
    resposta = await client.delete(f'/livro/{livro.id}', headers=headers)
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {'message': 'Livro deletado no MADR'}


async def test_deletar_livro_inexistente(client, headers):
    resposta = await client.delete('/livro/99', headers=headers)
    assert resposta.status_code == HTTPStatus.NOT_FOUND


async def test_deletar_livro_sem_token(client, livro):
    resposta = await client.delete(f'/livro/{livro.id}')
    assert resposta.status_code == HTTPStatus.UNAUTHORIZED


async def test_filtro_de_livros(client, headers, session):
    romancistas = [
        Romancista(nome='clarice lispector'),
        Romancista(nome='machado de assis'),
        Romancista(nome='josé de alencar'),
    ]
    session.add_all(romancistas)
    await session.commit()

    for ano, titulo, autor in [
        (1900, 'Café Da Manhã Dos Campeões', 1),
        (1900, 'Memórias Póstumas de Brás Cubas', 2),
        (1865, 'Iracema', 3),
    ]:
        await client.post(
            '/livro',
            json={'ano': ano, 'titulo': titulo, 'romancista_id': autor},
            headers=headers,
        )

    resposta = await client.get('/livro', params={'titulo': 'a', 'ano': 1900})
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {
        'livros': [
            {
                'id': 1,
                'ano': 1900,
                'titulo': 'café da manhã dos campeões',
                'romancista_id': 1,
            },
            {
                'id': 2,
                'ano': 1900,
                'titulo': 'memórias póstumas de brás cubas',
                'romancista_id': 2,
            },
        ]
    }


async def test_filtro_sem_resultado(client):
    resposta = await client.get('/livro', params={'titulo': 'inexistente'})
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.json() == {'livros': []}


async def test_paginacao_de_livros(client, headers, session, romancista):
    for i in range(25):
        session.add(
            Livro(
                ano=2000,
                titulo=f'livro numero {i:02d}',
                romancista_id=romancista.id,
            )
        )
    await session.commit()

    primeira = await client.get('/livro', params={'limit': 20})
    segunda = await client.get('/livro', params={'limit': 20, 'offset': 20})
    assert len(primeira.json()['livros']) == 20
    assert len(segunda.json()['livros']) == 5


async def test_paginacao_invalida(client):
    assert (await client.get('/livro', params={'limit': 0})).status_code == 422
    assert (
        await client.get('/livro', params={'offset': -1})
    ).status_code == 422
