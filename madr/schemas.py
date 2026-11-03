from pydantic import BaseModel, EmailStr, Field


class Message(BaseModel):
    message: str


class ContaSchema(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    senha: str = Field(min_length=7, max_length=72)


class ContaUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    senha: str = Field(min_length=7, max_length=72)


class ContaPublic(BaseModel):
    id: int
    email: EmailStr
    username: str


class ContaList(BaseModel):
    contas: list[ContaPublic]


class Token(BaseModel):
    access_token: str
    token_type: str


class RomancistaSchema(BaseModel):
    nome: str = Field(min_length=1, max_length=120)


class RomancistaUpdate(BaseModel):
    nome: str = Field(min_length=1, max_length=120)


class RomancistaPublic(BaseModel):
    id: int
    nome: str


class RomancistaList(BaseModel):
    romancistas: list[RomancistaPublic]


class LivroSchema(BaseModel):
    ano: int = Field(ge=0, le=2100)
    titulo: str = Field(min_length=1, max_length=200)
    romancista_id: int


class LivroUpdate(BaseModel):
    ano: int | None = Field(default=None, ge=0, le=2100)
    titulo: str | None = Field(default=None, min_length=1, max_length=200)


class LivroPublic(BaseModel):
    id: int
    ano: int
    titulo: str
    romancista_id: int


class LivroList(BaseModel):
    livros: list[LivroPublic]
