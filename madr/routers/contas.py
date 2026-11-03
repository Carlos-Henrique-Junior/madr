from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from madr.database import get_session
from madr.models import User
from madr.schemas import (
    ContaPublic,
    ContaSchema,
    ContaUpdate,
    Message,
    Token,
)
from madr.security import (
    criar_access_token,
    criar_hash_senha,
    get_current_user,
    verificar_senha,
)

router = APIRouter(tags=['contas'])

Session = Annotated[AsyncSession, Depends(get_session)]
ContaAtual = Annotated[User, Depends(get_current_user)]

CONFLITO = 'Conta já consta no MADR'


async def _conflito_de_conta(
    session: AsyncSession,
    email: str,
    username: str,
    ignorar_id: int | None = None,
) -> bool:
    query = select(User).where(
        or_(User.email == email, User.username == username)
    )
    if ignorar_id is not None:
        query = query.where(User.id != ignorar_id)
    return await session.scalar(query) is not None


@router.post(
    '/conta', status_code=HTTPStatus.CREATED, response_model=ContaPublic
)
@router.post(
    '/conta/',
    status_code=HTTPStatus.CREATED,
    response_model=ContaPublic,
    include_in_schema=False,
)
async def criar_conta(conta: ContaSchema, session: Session):
    email = conta.email.lower()
    if await _conflito_de_conta(session, email, conta.username):
        raise HTTPException(status.HTTP_409_CONFLICT, CONFLITO)

    user = User(
        username=conta.username,
        email=email,
        senha=criar_hash_senha(conta.senha),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.put('/conta/{conta_id}', response_model=ContaPublic)
async def atualizar_conta(
    conta_id: int,
    dados: ContaUpdate,
    session: Session,
    conta_atual: ContaAtual,
):
    if conta_atual.id != conta_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Não autorizado')

    email = dados.email.lower()
    if await _conflito_de_conta(
        session, email, dados.username, ignorar_id=conta_id
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, CONFLITO)

    conta_atual.username = dados.username
    conta_atual.email = email
    conta_atual.senha = criar_hash_senha(dados.senha)
    await session.commit()
    await session.refresh(conta_atual)
    return conta_atual


@router.delete('/conta/{conta_id}', response_model=Message)
async def deletar_conta(
    conta_id: int, session: Session, conta_atual: ContaAtual
):
    if conta_atual.id != conta_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Não autorizado')

    await session.delete(conta_atual)
    await session.commit()
    return {'message': 'Conta deletada com sucesso'}


@router.post('/token', response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session,
):
    user = await session.scalar(
        select(User).where(User.email == form.username.lower())
    )
    if user is None or not verificar_senha(form.password, user.senha):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, 'Email ou senha incorretos'
        )
    return {
        'access_token': criar_access_token({'sub': user.email}),
        'token_type': 'bearer',
    }


@router.post('/refresh-token', response_model=Token)
async def refresh_token(conta_atual: ContaAtual):
    return {
        'access_token': criar_access_token({'sub': conta_atual.email}),
        'token_type': 'bearer',
    }
