from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from madr.routers import contas, livros, romancistas
from madr.schemas import Message

app = FastAPI(title='MADR', description='Meu Acervo Digital de Romances')

app.include_router(contas.router)
app.include_router(livros.router)
app.include_router(romancistas.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
):
    """Todo erro da API responde no formato {"message": ...}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={'message': exc.detail},
        headers=getattr(exc, 'headers', None),
    )


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'Bem-vindo ao MADR'}
