from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from madr.database import get_session
from madr.models import Livro, Romancista, User
from madr.sanitize import sanitizar_nome
from madr.schemas import (
    LivroList,
    LivroPublic,
    LivroSchema,
    LivroUpdate,
    Message,
)
from madr.security import get_current_user

router = APIRouter(prefix='/livro', tags=['livros'])

Session = Annotated[AsyncSession, Depends(get_session)]
UsuarioAtual = Annotated[User, Depends(get_current_user)]

NAO_ENCONTRADO = 'Livro não consta no MADR'
CONFLITO = 'Livro já consta no MADR'
ROMANCISTA_INEXISTENTE = 'Romancista não consta no MADR'


async def _buscar_livro(session: AsyncSession, livro_id: int) -> Livro:
    livro = await session.scalar(select(Livro).where(Livro.id == livro_id))
    if livro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NAO_ENCONTRADO)
    return livro


async def _titulo_em_uso(
    session: AsyncSession, titulo: str, ignorar_id: int | None = None
) -> bool:
    query = select(Livro).where(Livro.titulo == titulo)
    if ignorar_id is not None:
        query = query.where(Livro.id != ignorar_id)
    return await session.scalar(query) is not None


@router.post('', status_code=HTTPStatus.CREATED, response_model=LivroPublic)
@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=LivroPublic,
    include_in_schema=False,
)
async def criar_livro(livro: LivroSchema, session: Session, _: UsuarioAtual):
    romancista = await session.get(Romancista, livro.romancista_id)
    if romancista is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, ROMANCISTA_INEXISTENTE)

    titulo = sanitizar_nome(livro.titulo)
    if await _titulo_em_uso(session, titulo):
        raise HTTPException(status.HTTP_409_CONFLICT, CONFLITO)

    db_livro = Livro(
        ano=livro.ano, titulo=titulo, romancista_id=livro.romancista_id
    )
    session.add(db_livro)
    await session.commit()
    await session.refresh(db_livro)
    return db_livro


@router.get('', response_model=LivroList)
@router.get('/', response_model=LivroList, include_in_schema=False)
async def listar_livros(
    session: Session,
    titulo: str | None = None,
    ano: int | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    query = select(Livro)
    if titulo:
        query = query.where(Livro.titulo.contains(sanitizar_nome(titulo)))
    if ano is not None:
        query = query.where(Livro.ano == ano)
    livros = (
        await session.scalars(
            query.order_by(Livro.id).limit(limit).offset(offset)
        )
    ).all()
    return {'livros': livros}


@router.get('/{livro_id}', response_model=LivroPublic)
async def ler_livro(livro_id: int, session: Session):
    return await _buscar_livro(session, livro_id)


@router.patch('/{livro_id}', response_model=LivroPublic)
async def atualizar_livro(
    livro_id: int,
    dados: LivroUpdate,
    session: Session,
    _: UsuarioAtual,
):
    livro = await _buscar_livro(session, livro_id)

    if dados.titulo is not None:
        titulo = sanitizar_nome(dados.titulo)
        if await _titulo_em_uso(session, titulo, ignorar_id=livro_id):
            raise HTTPException(status.HTTP_409_CONFLICT, CONFLITO)
        livro.titulo = titulo
    if dados.ano is not None:
        livro.ano = dados.ano

    await session.commit()
    await session.refresh(livro)
    return livro


@router.delete('/{livro_id}', response_model=Message)
async def deletar_livro(livro_id: int, session: Session, _: UsuarioAtual):
    livro = await _buscar_livro(session, livro_id)
    await session.delete(livro)
    await session.commit()
    return {'message': 'Livro deletado no MADR'}
