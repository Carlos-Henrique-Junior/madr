from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from madr.database import get_session
from madr.models import Livro, Romancista, User
from madr.sanitize import sanitizar_nome
from madr.schemas import (
    Message,
    RomancistaList,
    RomancistaPublic,
    RomancistaSchema,
    RomancistaUpdate,
)
from madr.security import get_current_user

router = APIRouter(prefix='/romancista', tags=['romancistas'])

Session = Annotated[AsyncSession, Depends(get_session)]
UsuarioAtual = Annotated[User, Depends(get_current_user)]

NAO_ENCONTRADO = 'Romancista não consta no MADR'
CONFLITO = 'Romancista já consta no MADR'


async def _buscar_romancista(
    session: AsyncSession, romancista_id: int
) -> Romancista:
    romancista = await session.scalar(
        select(Romancista).where(Romancista.id == romancista_id)
    )
    if romancista is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NAO_ENCONTRADO)
    return romancista


async def _nome_em_uso(
    session: AsyncSession, nome: str, ignorar_id: int | None = None
) -> bool:
    query = select(Romancista).where(Romancista.nome == nome)
    if ignorar_id is not None:
        query = query.where(Romancista.id != ignorar_id)
    return await session.scalar(query) is not None


@router.post(
    '', status_code=HTTPStatus.CREATED, response_model=RomancistaPublic
)
@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=RomancistaPublic,
    include_in_schema=False,
)
async def criar_romancista(
    romancista: RomancistaSchema, session: Session, _: UsuarioAtual
):
    nome = sanitizar_nome(romancista.nome)
    if await _nome_em_uso(session, nome):
        raise HTTPException(status.HTTP_409_CONFLICT, CONFLITO)

    db_romancista = Romancista(nome=nome)
    session.add(db_romancista)
    await session.commit()
    await session.refresh(db_romancista)
    return db_romancista


@router.get('', response_model=RomancistaList)
@router.get('/', response_model=RomancistaList, include_in_schema=False)
async def listar_romancistas(
    session: Session,
    nome: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    query = select(Romancista)
    if nome:
        query = query.where(Romancista.nome.contains(sanitizar_nome(nome)))
    romancistas = (
        await session.scalars(
            query.order_by(Romancista.id).limit(limit).offset(offset)
        )
    ).all()
    return {'romancistas': romancistas}


@router.get('/{romancista_id}', response_model=RomancistaPublic)
async def ler_romancista(romancista_id: int, session: Session):
    return await _buscar_romancista(session, romancista_id)


@router.patch('/{romancista_id}', response_model=RomancistaPublic)
@router.put('/{romancista_id}', response_model=RomancistaPublic)
async def atualizar_romancista(
    romancista_id: int,
    dados: RomancistaUpdate,
    session: Session,
    _: UsuarioAtual,
):
    romancista = await _buscar_romancista(session, romancista_id)
    nome = sanitizar_nome(dados.nome)
    if await _nome_em_uso(session, nome, ignorar_id=romancista_id):
        raise HTTPException(status.HTTP_409_CONFLICT, CONFLITO)

    romancista.nome = nome
    await session.commit()
    await session.refresh(romancista)
    return romancista


@router.delete('/{romancista_id}', response_model=Message)
async def deletar_romancista(
    romancista_id: int, session: Session, _: UsuarioAtual
):
    romancista = await _buscar_romancista(session, romancista_id)
    # Apaga os livros da romancista antes de removê-la; o FK também declara
    # ON DELETE CASCADE, mas o SQLite só o respeita com PRAGMA ligado.
    await session.execute(
        sa_delete(Livro).where(Livro.romancista_id == romancista_id)
    )
    await session.delete(romancista)
    await session.commit()
    return {'message': 'Romancista deletada no MADR'}
