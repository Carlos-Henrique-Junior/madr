from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, decode, encode
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from madr.database import get_session
from madr.models import User
from madr.settings import Settings

settings = Settings()
pwd_context = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token', auto_error=False)

NAO_AUTORIZADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail='Não autorizado'
)


def criar_hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha, senha_hash)


def criar_access_token(dados: dict) -> str:
    payload = dados.copy()
    expira = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({'exp': expira})
    return encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise NAO_AUTORIZADO
    try:
        payload = decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email = payload.get('sub')
    except (DecodeError, ExpiredSignatureError):
        raise NAO_AUTORIZADO
    if not email:
        raise NAO_AUTORIZADO
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        raise NAO_AUTORIZADO
    return user
