import pytest

from madr.models import Livro, Romancista


@pytest.fixture
async def logado(client, usuario):
    await client.post(
        '/login', data={'email': usuario.email, 'senha': '1234567'}
    )
    return client


async def test_login_de_volta_para_painel(client, usuario):
    resposta = await client.post(
        '/login', data={'email': usuario.email.upper(), 'senha': '1234567'}
    )
    assert resposta.status_code == 303
    assert resposta.headers['location'] == '/painel'


async def test_paginas_redirecionam_sem_cookie(client):
    for rota in (
        '/painel',
        '/livros',
        '/romancistas',
        '/livros/novo',
        '/romancistas/novo',
    ):
        resposta = await client.get(rota)
        assert resposta.status_code == 303
        assert resposta.headers['location'] == '/login'


async def test_editar_livro_abre_formulario(client, logado, livro, romancista):
    resposta = await client.get(f'/livros/{livro.id}/editar')
    assert resposta.status_code == 200
    assert 'café da manhã dos campeões' in resposta.text
    assert romancista.nome in resposta.text


async def test_editar_livro_inexistente(client, logado):
    resposta = await client.get('/livros/999/editar')
    assert resposta.status_code == 303
    assert '/livros' in resposta.headers['location']


async def test_salvar_livro_atualiza(client, logado, livro, session):
    resposta = await client.post(
        f'/livros/{livro.id}',
        data={
            'titulo': 'Grande Sertão: Veredas',
            'ano': '1956',
            'romancista_id': str(livro.romancista_id),
        },
    )
    assert resposta.status_code == 303

    atualizado = await session.get(Livro, livro.id)
    await session.refresh(atualizado)
    assert atualizado.titulo == 'grande sertão veredas'
    assert atualizado.ano == 1956


async def test_salvar_livro_com_titulo_de_outro(
    client, logado, livro, session, romancista
):
    outro = Livro(ano=2000, titulo='outro livro', romancista_id=romancista.id)
    session.add(outro)
    await session.commit()

    resposta = await client.post(
        f'/livros/{outro.id}',
        data={
            'titulo': 'Café da manhã dos campeões',
            'ano': '2000',
            'romancista_id': str(romancista.id),
        },
    )
    assert resposta.status_code == 400
    assert 'já usa esse título' in resposta.text


async def test_criar_livro_sem_titulo(client, logado, romancista):
    resposta = await client.post(
        '/livros',
        data={
            'titulo': '   ',
            'ano': '2000',
            'romancista_id': str(romancista.id),
        },
    )
    assert resposta.status_code == 400
    assert 'Informe o título' in resposta.text


async def test_criar_livro_sem_romancista_selecionada(client, logado):
    resposta = await client.post(
        '/livros', data={'titulo': 'Livro', 'ano': '2000', 'romancista_id': ''}
    )
    assert resposta.status_code == 400
    assert 'Escolha uma romancista' in resposta.text


async def test_criar_livro_duplicado(client, logado, livro, romancista):
    resposta = await client.post(
        '/livros',
        data={
            'titulo': 'Café da manhã dos campeões',
            'ano': '1973',
            'romancista_id': str(romancista.id),
        },
    )
    assert resposta.status_code == 400
    assert 'já consta no MADR' in resposta.text


async def test_atualizar_romancista(client, logado, romancista, session):
    resposta = await client.post(
        f'/romancistas/{romancista.id}', data={'nome': 'Manuel Bandeira'}
    )
    assert resposta.status_code == 303

    atualizada = await session.get(Romancista, romancista.id)
    await session.refresh(atualizada)
    assert atualizada.nome == 'manuel bandeira'


async def test_romancista_com_nome_vazio(client, logado, romancista):
    resposta = await client.post(
        f'/romancistas/{romancista.id}', data={'nome': '  '}
    )
    assert resposta.status_code == 400
    assert 'Informe o nome' in resposta.text


async def test_romancista_com_nome_de_outra(
    client, logado, romancista, session
):
    outra = Romancista(nome='outra pessoa')
    session.add(outra)
    await session.commit()

    resposta = await client.post(
        f'/romancistas/{outra.id}', data={'nome': 'Clarice Lispector'}
    )
    assert resposta.status_code == 400
    assert 'já usa esse nome' in resposta.text


async def test_editar_romancista_inexistente(client, logado):
    resposta = await client.get('/romancistas/999/editar')
    assert resposta.status_code == 303
    assert '/romancistas' in resposta.headers['location']


async def test_salvar_romancista_inexistente(client, logado):
    resposta = await client.post('/romancistas/999', data={'nome': 'x'})
    assert resposta.status_code == 303


async def test_salvar_livro_inexistente(client, logado):
    resposta = await client.post(
        '/livros/999',
        data={'titulo': 'x', 'ano': '2000', 'romancista_id': '1'},
    )
    assert resposta.status_code == 303


async def test_tabela_romancistas_filtra(client, logado, romancista):
    parcial = await client.get('/romancistas/tabela', params={'nome': 'clari'})
    assert 'clarice lispector' in parcial.text
    assert (
        'Nenhuma romancista encontrada'
        in (
            await client.get('/romancistas/tabela', params={'nome': 'zzz'})
        ).text
    )


async def test_paginacao_de_livros_na_web(client, logado, session, romancista):
    for i in range(25):
        session.add(
            Livro(
                ano=2000,
                titulo=f'livro numero {i:02d}',
                romancista_id=romancista.id,
            )
        )
    await session.commit()

    primeira = await client.get('/livros')
    segunda = await client.get('/livros', params={'page': 2})
    assert 'página 1 de 2' in primeira.text
    assert 'página 2 de 2' in segunda.text


async def test_paginacao_de_romancistas_na_web(client, logado, session):
    for i in range(25):
        session.add(Romancista(nome=f'romancista {i:02d}'))
    await session.commit()

    segunda = await client.get('/romancistas', params={'page': 2})
    assert 'página 2 de 2' in segunda.text
