from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from madr.routers import contas, livros, romancistas
from madr.schemas import Message
from madr.web import routes as web
from madr.web.routes import BASE as WEB_BASE

app = FastAPI(title='MADR', description='Meu Acervo Digital de Romances')

app.include_router(contas.router)
app.include_router(livros.router)
app.include_router(romancistas.router)
app.include_router(web.router)

app.mount(
    '/static', StaticFiles(directory=str(WEB_BASE / 'static')), name='static'
)


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


@app.get('/health', status_code=HTTPStatus.OK, response_model=Message)
def health():
    return {'message': 'ok'}
