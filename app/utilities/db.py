import socket

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()


def check_database():
    """Devuelve (ok, detalle) ejecutando un SELECT 1 contra la base configurada."""
    try:
        db.session.execute(text("SELECT 1"))
        return True, db.engine.dialect.name
    except Exception as exc:  # noqa: BLE001 - se muestra el error en el panel
        db.session.rollback()
        return False, str(exc.__class__.__name__)


def node_name():
    """Nombre del servidor que atiende la petición (sirve para ver el failover)."""
    return current_app.config.get("NODE_NAME") or socket.gethostname()
