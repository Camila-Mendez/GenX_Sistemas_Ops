import os

from sqlalchemy.engine import URL

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Motor -> driver de SQLAlchemy
DRIVERS = {
    "mysql": "mysql+pymysql",
    "postgresql": "postgresql+psycopg2",
    "sqlserver": "mssql+pyodbc",
}

DEFAULT_PORTS = {"mysql": 3306, "postgresql": 5432, "sqlserver": 1433}


def build_database_uri():
    """Arma la cadena de conexión a partir de variables de entorno.

    Prioridad:
      1. DATABASE_URL (cadena completa de SQLAlchemy).
      2. DB_ENGINE + DB_HOST + DB_PORT + DB_NAME + DB_USER + DB_PASSWORD.
      3. SQLite local (solo para desarrollo).
    """
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    engine = os.getenv("DB_ENGINE", "sqlite").lower()

    if engine == "sqlite":
        return "sqlite:///" + os.path.join(BASE_DIR, "genx_dev.db")

    if engine not in DRIVERS:
        raise RuntimeError(
            f"DB_ENGINE='{engine}' no soportado. Usa: sqlite, mysql, postgresql o sqlserver."
        )

    query = {}
    if engine == "sqlserver":
        query = {
            "driver": os.getenv("DB_ODBC_DRIVER", "ODBC Driver 18 for SQL Server"),
            "TrustServerCertificate": "yes",
        }
    elif engine == "mysql":
        query = {"charset": "utf8mb4"}

    # URL.create escapa correctamente contraseñas con caracteres especiales (@, :, /, ...)
    return URL.create(
        drivername=DRIVERS[engine],
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", DEFAULT_PORTS[engine])),
        database=os.getenv("DB_NAME", "genx_portal"),
        query=query,
    ).render_as_string(hide_password=False)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "devkey-cambiar-en-produccion")
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # pool_pre_ping descarta conexiones muertas: clave cuando la IP virtual
    # cambia del servidor activo al pasivo durante un failover.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    # Nombre con el que se identifica este nodo en el panel (activo / pasivo)
    NODE_NAME = os.getenv("GENX_NODE_NAME")
