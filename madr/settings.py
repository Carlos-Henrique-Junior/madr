from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida do ambiente/.env; defaults servem para teste local."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    DATABASE_URL: str = 'sqlite+aiosqlite:///./madr.sqlite3'
    SECRET_KEY: str = 'troque-esta-chave-em-producao'
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
