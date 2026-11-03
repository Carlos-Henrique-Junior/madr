from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

table_registry = registry()


@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    senha: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime, init=False, server_default=func.now()
    )


@table_registry.mapped_as_dataclass
class Romancista:
    __tablename__ = 'romancistas'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    nome: Mapped[str] = mapped_column(unique=True)
    livros: Mapped[list['Livro']] = relationship(
        init=False,
        back_populates='romancista',
        passive_deletes=True,
    )


@table_registry.mapped_as_dataclass
class Livro:
    __tablename__ = 'livros'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    ano: Mapped[int]
    titulo: Mapped[str] = mapped_column(unique=True)
    romancista_id: Mapped[int] = mapped_column(
        ForeignKey('romancistas.id', ondelete='CASCADE')
    )
    romancista: Mapped['Romancista'] = relationship(
        init=False, back_populates='livros'
    )
