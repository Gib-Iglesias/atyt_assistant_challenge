"""Configuracion de la app y ajustes de conexion de SQLite."""
import logging

from django.apps import AppConfig
from django.db.backends.signals import connection_created

log = logging.getLogger(__name__)


def _tune_sqlite(sender, connection, **kwargs) -> None:
    """
    Aplica los PRAGMA que hacen viable compartir un fichero SQLite entre el
    servicio django y el servicio api.

    - journal_mode=WAL: lectores y escritor no se bloquean entre si.
    - busy_timeout: reintenta en vez de fallar cuando el escritor esta ocupado.
    - foreign_keys: SQLite no las aplica por defecto.

    En cualquier otro motor no se hace nada.
    """
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Asistente de soporte"

    def ready(self) -> None:
        connection_created.connect(_tune_sqlite, dispatch_uid="core.tune_sqlite")
