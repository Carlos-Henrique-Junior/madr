from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jwt import DecodeError, ExpiredSignatureError, decode
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from madr.database import get_session
from madr.models import Livro, Romancista, User
from madr.sanitize import sanitizar_nome
from madr.security import criar_access_token, settings, verificar_senha

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / 'templates'))

router = APIRouter(include_in_schema=False)
Session = Annotated[AsyncSession, Depends(get_session)]

PAGINA = 20
ANO_MAX = 2100
COOKIE = 'access_token'


async def usuario_do_cookie(
    request: Request, session: AsyncSession
) -> User | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    try:
        payload = decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except (DecodeError, ExpiredSignatureError):
        return None
    email = payload.get('sub')
    if not email:
        return None
    return await session.scalar(select(User).where(User.email == email))


def _redirecionar(url: str, **params) -> RedirectResponse:
    if params:
        url = f'{url}?{urlencode(params)}'
    return RedirectResponse(url, status_code=303)


@router.get('/login', response_class=HTMLResponse)
async def pagina_login(request: Request):
    return templates.TemplateResponse(request, 'login.html', {'erro': None})


@router.post('/login', response_class=HTMLResponse)
async def entrar(
    request: Request,
    session: Session,
    email: Annotated[str, Form()],
    senha: Annotated[str, Form()],
):
    user = await session.scalar(
        select(User).where(User.email == email.strip().lower())
    )
    if user is None or not verificar_senha(senha, user.senha):
        return templates.TemplateResponse(
            request,
            'login.html',
            {'erro': 'E-mail ou senha incorretos.'},
            status_code=400,
        )

    resposta = _redirecionar('/painel')
    resposta.set_cookie(
        COOKIE,
        criar_access_token({'sub': user.email}),
        httponly=True,
        samesite='lax',
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return resposta


@router.post('/sair')
async def sair():
    resposta = _redirecionar('/login')
    resposta.delete_cookie(COOKIE)
    return resposta


@router.get('/painel', response_class=HTMLResponse)
async def painel(request: Request, session: Session):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')

    total_livros = await session.scalar(
        select(func.count()).select_from(Livro)
    )
    total_romancistas = await session.scalar(
        select(func.count()).select_from(Romancista)
    )
    recentes = (
        await session.scalars(select(Livro).order_by(Livro.id.desc()).limit(5))
    ).all()

    return templates.TemplateResponse(
        request,
        'painel.html',
        {
            'user': user,
            'total_livros': total_livros,
            'total_romancistas': total_romancistas,
            'recentes': recentes,
            'pagina_ativa': 'painel',
        },
    )


async def _dados_livros(
    session: AsyncSession, titulo: str, ano: str, page: int
):
    query = select(Livro)
    if titulo:
        query = query.where(Livro.titulo.contains(sanitizar_nome(titulo)))
    if ano and ano.isdigit():
        query = query.where(Livro.ano == int(ano))

    total = await session.scalar(
        select(func.count()).select_from(query.subquery())
    )
    livros = (
        await session.scalars(
            query.order_by(Livro.id).limit(PAGINA).offset((page - 1) * PAGINA)
        )
    ).all()
    return livros, total


@router.get('/livros', response_class=HTMLResponse)
async def pagina_livros(
    request: Request,
    session: Session,
    titulo: str = '',
    ano: str = '',
    page: int = 1,
):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')

    page = max(page, 1)
    livros, total = await _dados_livros(session, titulo, ano, page)
    return templates.TemplateResponse(
        request,
        'livros.html',
        {
            'user': user,
            'livros': livros,
            'total': total,
            'titulo': titulo,
            'ano': ano,
            'page': page,
            'paginas': max((total + PAGINA - 1) // PAGINA, 1),
            'pagina_ativa': 'livros',
        },
    )


@router.get('/livros/tabela', response_class=HTMLResponse)
async def tabela_livros(
    request: Request,
    session: Session,
    titulo: str = '',
    ano: str = '',
    page: int = 1,
):
    if await usuario_do_cookie(request, session) is None:
        return HTMLResponse('', status_code=401)

    page = max(page, 1)
    livros, total = await _dados_livros(session, titulo, ano, page)
    return templates.TemplateResponse(
        request,
        'partials/tabela_livros.html',
        {
            'livros': livros,
            'total': total,
            'titulo': titulo,
            'ano': ano,
            'page': page,
            'paginas': max((total + PAGINA - 1) // PAGINA, 1),
        },
    )


@router.get('/livros/novo', response_class=HTMLResponse)
async def novo_livro(request: Request, session: Session):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')
    romancistas = (await session.scalars(select(Romancista))).all()
    return templates.TemplateResponse(
        request,
        'livro_form.html',
        {
            'user': user,
            'livro': None,
            'romancistas': romancistas,
            'erro': None,
            'pagina_ativa': 'livros',
        },
    )


async def _validar_livro(
    session: AsyncSession,
    titulo: str,
    ano: str,
    romancista_id: str,
    ignorar_id: int | None,
) -> str | None:
    if not titulo.strip():
        return 'Informe o título.'
    if not ano.isdigit() or not 0 <= int(ano) <= ANO_MAX:
        return 'Ano precisa ser um número entre 0 e 2100.'
    if not romancista_id.isdigit():
        return 'Escolha uma romancista.'
    if await session.get(Romancista, int(romancista_id)) is None:
        return 'Escolha uma romancista.'

    query = select(Livro).where(Livro.titulo == sanitizar_nome(titulo))
    if ignorar_id is not None:
        query = query.where(Livro.id != ignorar_id)
    if await session.scalar(query):
        return (
            'Outro livro já usa esse título.'
            if ignorar_id is not None
            else 'Livro já consta no MADR.'
        )
    return None


@router.post('/livros', response_class=HTMLResponse)
async def criar_livro_web(
    request: Request,
    session: Session,
    titulo: Annotated[str, Form()] = '',
    ano: Annotated[str, Form()] = '',
    romancista_id: Annotated[str, Form()] = '',
):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')

    romancistas = (await session.scalars(select(Romancista))).all()
    erro = await _validar_livro(
        session, titulo, ano, romancista_id, ignorar_id=None
    )
    nome = sanitizar_nome(titulo)

    if erro:
        return templates.TemplateResponse(
            request,
            'livro_form.html',
            {
                'user': user,
                'livro': None,
                'romancistas': romancistas,
                'erro': erro,
                'pagina_ativa': 'livros',
            },
            status_code=400,
        )

    session.add(
        Livro(ano=int(ano), titulo=nome, romancista_id=int(romancista_id))
    )
    await session.commit()
    return _redirecionar('/livros', ok='Livro cadastrado.')


@router.get('/livros/{livro_id}/editar', response_class=HTMLResponse)
async def editar_livro(request: Request, livro_id: int, session: Session):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')
    livro = await session.get(Livro, livro_id)
    if livro is None:
        return _redirecionar('/livros', erro='Livro não encontrado.')
    romancistas = (await session.scalars(select(Romancista))).all()
    return templates.TemplateResponse(
        request,
        'livro_form.html',
        {
            'user': user,
            'livro': livro,
            'romancistas': romancistas,
            'erro': None,
            'pagina_ativa': 'livros',
        },
    )


@router.post('/livros/{livro_id}', response_class=HTMLResponse)
async def salvar_livro_web(
    request: Request,
    livro_id: int,
    session: Session,
    titulo: Annotated[str, Form()] = '',
    ano: Annotated[str, Form()] = '',
    romancista_id: Annotated[str, Form()] = '',
):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')
    livro = await session.get(Livro, livro_id)
    if livro is None:
        return _redirecionar('/livros', erro='Livro não encontrado.')

    romancistas = (await session.scalars(select(Romancista))).all()
    erro = await _validar_livro(
        session, titulo, ano, romancista_id, ignorar_id=livro_id
    )
    nome = sanitizar_nome(titulo)

    if erro:
        return templates.TemplateResponse(
            request,
            'livro_form.html',
            {
                'user': user,
                'livro': livro,
                'romancistas': romancistas,
                'erro': erro,
                'pagina_ativa': 'livros',
            },
            status_code=400,
        )

    livro.titulo = nome
    livro.ano = int(ano)
    livro.romancista_id = int(romancista_id)
    await session.commit()
    return _redirecionar('/livros', ok='Livro atualizado.')


@router.post('/livros/{livro_id}/excluir', response_class=HTMLResponse)
async def excluir_livro_web(
    request: Request,
    livro_id: int,
    session: Session,
    titulo: str = '',
    ano: str = '',
    page: int = 1,
):
    if await usuario_do_cookie(request, session) is None:
        return HTMLResponse('', status_code=401)
    livro = await session.get(Livro, livro_id)
    if livro is not None:
        await session.delete(livro)
        await session.commit()

    livros, total = await _dados_livros(session, titulo, ano, max(page, 1))
    return templates.TemplateResponse(
        request,
        'partials/tabela_livros.html',
        {
            'livros': livros,
            'total': total,
            'titulo': titulo,
            'ano': ano,
            'page': max(page, 1),
            'paginas': max((total + PAGINA - 1) // PAGINA, 1),
        },
    )


async def _dados_romancistas(session: AsyncSession, nome: str, page: int):
    query = select(Romancista)
    if nome:
        query = query.where(Romancista.nome.contains(sanitizar_nome(nome)))

    total = await session.scalar(
        select(func.count()).select_from(query.subquery())
    )
    romancistas = (
        await session.scalars(
            query.order_by(Romancista.id)
            .limit(PAGINA)
            .offset((page - 1) * PAGINA)
        )
    ).all()
    return romancistas, total


@router.get('/romancistas', response_class=HTMLResponse)
async def pagina_romancistas(
    request: Request, session: Session, nome: str = '', page: int = 1
):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')

    page = max(page, 1)
    romancistas, total = await _dados_romancistas(session, nome, page)
    return templates.TemplateResponse(
        request,
        'romancistas.html',
        {
            'user': user,
            'romancistas': romancistas,
            'total': total,
            'nome': nome,
            'page': page,
            'paginas': max((total + PAGINA - 1) // PAGINA, 1),
            'pagina_ativa': 'romancistas',
        },
    )


@router.get('/romancistas/tabela', response_class=HTMLResponse)
async def tabela_romancistas(
    request: Request, session: Session, nome: str = '', page: int = 1
):
    if await usuario_do_cookie(request, session) is None:
        return HTMLResponse('', status_code=401)
    page = max(page, 1)
    romancistas, total = await _dados_romancistas(session, nome, page)
    return templates.TemplateResponse(
        request,
        'partials/tabela_romancistas.html',
        {
            'romancistas': romancistas,
            'total': total,
            'nome': nome,
            'page': page,
            'paginas': max((total + PAGINA - 1) // PAGINA, 1),
        },
    )


@router.get('/romancistas/novo', response_class=HTMLResponse)
async def novo_romancista(request: Request, session: Session):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')
    return templates.TemplateResponse(
        request,
        'romancista_form.html',
        {
            'user': user,
            'romancista': None,
            'erro': None,
            'pagina_ativa': 'romancistas',
        },
    )


@router.post('/romancistas', response_class=HTMLResponse)
async def criar_romancista_web(
    request: Request, session: Session, nome: Annotated[str, Form()]
):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')

    limpo = sanitizar_nome(nome)
    erro = None
    if not limpo:
        erro = 'Informe o nome.'
    elif await session.scalar(
        select(Romancista).where(Romancista.nome == limpo)
    ):
        erro = 'Romancista já consta no MADR.'

    if erro:
        return templates.TemplateResponse(
            request,
            'romancista_form.html',
            {
                'user': user,
                'romancista': None,
                'erro': erro,
                'pagina_ativa': 'romancistas',
            },
            status_code=400,
        )

    session.add(Romancista(nome=limpo))
    await session.commit()
    return _redirecionar('/romancistas', ok='Romancista cadastrada.')


@router.get('/romancistas/{romancista_id}/editar', response_class=HTMLResponse)
async def editar_romancista(
    request: Request, romancista_id: int, session: Session
):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')
    romancista = await session.get(Romancista, romancista_id)
    if romancista is None:
        return _redirecionar('/romancistas', erro='Romancista não encontrada.')
    return templates.TemplateResponse(
        request,
        'romancista_form.html',
        {
            'user': user,
            'romancista': romancista,
            'erro': None,
            'pagina_ativa': 'romancistas',
        },
    )


@router.post('/romancistas/{romancista_id}', response_class=HTMLResponse)
async def salvar_romancista_web(
    request: Request,
    romancista_id: int,
    session: Session,
    nome: Annotated[str, Form()],
):
    user = await usuario_do_cookie(request, session)
    if user is None:
        return _redirecionar('/login')
    romancista = await session.get(Romancista, romancista_id)
    if romancista is None:
        return _redirecionar('/romancistas', erro='Romancista não encontrada.')

    limpo = sanitizar_nome(nome)
    erro = None
    if not limpo:
        erro = 'Informe o nome.'
    elif await session.scalar(
        select(Romancista).where(
            Romancista.nome == limpo, Romancista.id != romancista_id
        )
    ):
        erro = 'Outra romancista já usa esse nome.'

    if erro:
        return templates.TemplateResponse(
            request,
            'romancista_form.html',
            {
                'user': user,
                'romancista': romancista,
                'erro': erro,
                'pagina_ativa': 'romancistas',
            },
            status_code=400,
        )

    romancista.nome = limpo
    await session.commit()
    return _redirecionar('/romancistas', ok='Romancista atualizada.')


@router.post(
    '/romancistas/{romancista_id}/excluir', response_class=HTMLResponse
)
async def excluir_romancista_web(
    request: Request,
    romancista_id: int,
    session: Session,
    nome: str = '',
    page: int = 1,
):
    if await usuario_do_cookie(request, session) is None:
        return HTMLResponse('', status_code=401)
    romancista = await session.get(Romancista, romancista_id)
    if romancista is not None:
        await session.execute(
            Livro.__table__.delete().where(
                Livro.romancista_id == romancista_id
            )
        )
        await session.delete(romancista)
        await session.commit()

    romancistas, total = await _dados_romancistas(session, nome, max(page, 1))
    return templates.TemplateResponse(
        request,
        'partials/tabela_romancistas.html',
        {
            'romancistas': romancistas,
            'total': total,
            'nome': nome,
            'page': max(page, 1),
            'paginas': max((total + PAGINA - 1) // PAGINA, 1),
        },
    )
