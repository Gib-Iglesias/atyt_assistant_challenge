"""
Configuracion del servicio de IA, tipada y leida del entorno.

Comparte los mismos nombres de variable que Django (DATABASE_URL, JWT_SECRET,
LLM_*). Es el mismo .env para los dos servicios.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # base de datos: misma que Django, en el volumen compartido
    database_url: str = Field(default="sqlite:////data/db.sqlite3")

    # jwt: mismo secreto con que Django firma
    jwt_secret: str = Field(default="inseguro-solo-para-desarrollo")
    jwt_algorithm: str = Field(default="HS256")
    jwt_issuer: str = Field(default="atyt-assistant-django")

    # proveedor de LLM
    llm_provider: str = Field(default="fake")
    llm_model: str = Field(default="")
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="")
    llm_max_concurrency: int = Field(default=20)
    llm_max_context_tokens: int = Field(default=6000)
    llm_timeout_seconds: int = Field(default=60)
    llm_queue_max_size: int = Field(default=200)
    llm_queue_timeout_seconds: int = Field(default=30)
    fake_llm_token_delay_ms: int = Field(default=25)

    # recuperacion
    retrieval_top_k: int = Field(default=6)
    # Umbral de escalado. Los BM25 invertidos de este corpus caen en el rango
    # 2-10; por debajo de ~1.5 el fragmento no tiene que ver con la pregunta.
    # Ver docs/DECISIONES.md.
    retrieval_min_score: float = Field(default=1.5)

    rate_limit_per_minute: int = Field(default=60)

    @property
    def sqlite_path(self) -> str | None:
        """Ruta del fichero si DATABASE_URL es SQLite; None en otro caso."""
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            return "/" + self.database_url[len(prefix):].lstrip("/")
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
