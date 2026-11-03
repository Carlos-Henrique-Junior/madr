import pytest
from sqlalchemy import select

from madr.models import Livro, Romancista


@pytest.fixture
async def logado(client, usuario):
    resposta = await client.post(
        '/login', data={'email': usuario.email, 'senha': '1234567'}
    )
    assert resposta.status_code == 303
    return client


async def test_painel_exige_login(client):
    resposta = await client.get('/painel')
    assert resposta.status_code == 303
    assert resposta.headers['location'] == '/login'


async def test_login_com_senha_errada(client, usuario):
    resposta = await client.post(
        '/login', data={'email': usuario.email, 'senha': 'errada'}
    )
    assert resposta.status_code == 400
    assert 'incorretos' in resposta.text


async def test_login_grava_cookie_e_abre_painel(client, usuario):
    resposta = await client.post(
        '/login', data={'email': usuario.email, 'senha': '1234567'}
    )
    assert resposta.status_code == 303
    assert resposta.headers['location'] == '/painel'
    assert 'access_token' in client.cookies

    painel = await client.get('/painel')
    assert painel.status_code == 200
    assert 'Painel' in painel.text


async def test_logout_limpa_cookie(client, logado):
    resposta = await client.post('/sair')
    assert resposta.status_code == 303
    assert (await client.get('/painel')).status_code == 303


async def test_criar_romancista_pela_web(client, logado, session):
    resposta = await client.post(
        '/romancistas', data={'nome': 'Clarice Lispector'}
    )
    assert resposta.status_code == 303
    romancista = await session.scalar(
        select(Romancista).where(Romancista.nome == 'clarice lispector')
    )
    assert romancista is not None


async def test_romancista_duplicada_pela_web(client, logado, romancista):
    resposta = await client.post(
        '/romancistas', data={'nome': 'Clarice Lispector'}
    )
    assert resposta.status_code == 400
    assert 'já consta' in resposta.text


async def test_criar_livro_pela_web(client, logado, session, romancista):
    resposta = await client.post(
        '/livros',
        data={
            'titulo': 'A Hora da Estrela',
            'ano': '1977',
            'romancista_id': str(romancista.id),
        },
    )
    assert resposta.status_code == 303

    livro = await session.scalar(
        select(Livro).where(Livro.titulo == 'a hora da estrela')
    )
    assert livro is not None
    assert livro.ano == 1977


async def test_livro_com_ano_invalido(client, logado, romancista):
    resposta = await client.post(
        '/livros',
        data={
            'titulo': 'Livro X',
            'ano': 'mil',
            'romancista_id': str(romancista.id),
        },
    )
    assert resposta.status_code == 400
    assert 'Ano precisa' in resposta.text


async def test_pagina_livros_lista_e_filtra(client, logado, livro):
    pagina = await client.get('/livros')
    assert pagina.status_code == 200
    assert 'café da manhã dos campeões' in pagina.text

    parcial = await client.get('/livros/tabela', params={'titulo': 'café'})
    assert parcial.status_code == 200
    assert 'café da manhã dos campeões' in parcial.text

    vazio = await client.get('/livros/tabela', params={'titulo': 'zzz'})
    assert 'Nenhum livro encontrado' in vazio.text


async def test_excluir_livro_pela_web(client, logado, livro):
    resposta = await client.post(f'/livros/{livro.id}/excluir')
    assert resposta.status_code == 200
    assert 'Nenhum livro encontrado' in resposta.text
    assert (await client.get(f'/livro/{livro.id}')).status_code == 404


async def test_excluir_romancista_pela_web(client, logado, romancista, livro):
    resposta = await client.post(f'/romancistas/{romancista.id}/excluir')
    assert resposta.status_code == 200
    assert (
        await client.get(f'/romancista/{romancista.id}')
    ).status_code == 404
    assert (await client.get(f'/livro/{livro.id}')).status_code == 404


async def test_formulario_de_livro_sem_romancistas(client, logado):
    resposta = await client.get('/livros/novo')
    assert resposta.status_code == 200
    assert 'Cadastre uma primeiro' in resposta.text


async def test_rotas_web_sem_login(client):
    for rota in ('/livros', '/romancistas', '/livros/novo'):
        assert (await client.get(rota)).status_code == 303


async def test_tabela_sem_login_retorna_401(client):
    resposta = await client.get('/livros/tabela')
    assert resposta.status_code == 401
