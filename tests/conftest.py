import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from madr.app import app
from madr.database import get_session
from madr.models import Livro, Romancista, User, table_registry
from madr.security import criar_hash_senha


@pytest.fixture
async def session():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
    await engine.dispose()


@pytest.fixture
async def client(session):
    async def _get_session():
        yield session

    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def usuario(session):
    user = User(
        username='dunossauro',
        email='dudu@dudu.com',
        senha=criar_hash_senha('1234567'),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def token(client, usuario):
    resposta = await client.post(
        '/token',
        data={'username': usuario.email, 'password': '1234567'},
    )
    return resposta.json()['access_token']


@pytest.fixture
def headers(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
async def romancista(session):
    romancista = Romancista(nome='clarice lispector')
    session.add(romancista)
    await session.commit()
    await session.refresh(romancista)
    return romancista


@pytest.fixture
async def livro(session, romancista):
    livro = Livro(
        ano=1973,
        titulo='café da manhã dos campeões',
        romancista_id=romancista.id,
    )
    session.add(livro)
    await session.commit()
    await session.refresh(livro)
    return livro
