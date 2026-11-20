"""Las pruebas corren contra un MySQL real usando los scripts de sql/.

Requiere una base de pruebas SEPARADA y un usuario con permisos de DDL:

    CREATE DATABASE genx_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER 'genx_test'@'localhost' IDENTIFIED BY 'genx_test';
    GRANT ALL PRIVILEGES ON genx_test.* TO 'genx_test'@'localhost';

Variables (opcionales): TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME, TEST_DB_USER, TEST_DB_PASSWORD.
Si no hay conexión, las pruebas se omiten.
"""
import os
from pathlib import Path

import pymysql
import pytest
from werkzeug.security import generate_password_hash

TEST_DB = {
    "DB_HOST": os.getenv("TEST_DB_HOST", "127.0.0.1"),
    "DB_PORT": os.getenv("TEST_DB_PORT", "3306"),
    "DB_NAME": os.getenv("TEST_DB_NAME", "genx_test"),
    "DB_USER": os.getenv("TEST_DB_USER", "genx_test"),
    "DB_PASSWORD": os.getenv("TEST_DB_PASSWORD", "genx_test"),
}
os.environ.update(TEST_DB)
os.environ["GENX_NODE_NAME"] = "nodo-test"

from app import app as flask_app  # noqa: E402
from app.utilities.db_connection import get_connection  # noqa: E402

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
TABLES = ["solicitud_detalle", "solicitudes", "bitacora_login", "mensajes_contacto", "planes", "usuarios"]


def run_sql_script(cur, filename):
    """Ejecuta un script de sql/ (sin su línea USE) sentencia por sentencia."""
    text = (SQL_DIR / filename).read_text(encoding="utf-8")
    for statement in text.split(";"):
        code = "\n".join(l for l in statement.splitlines()
                         if l.strip() and not l.strip().startswith("--"))
        if code and not code.upper().startswith("USE "):
            cur.execute(code)


@pytest.fixture()
def app():
    try:
        conn = get_connection()
    except pymysql.err.OperationalError as exc:
        pytest.skip(f"MySQL de pruebas no disponible: {exc}")

    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in TABLES:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        run_sql_script(cur, "02_modelo_fisico.sql")
        run_sql_script(cur, "03_datos_iniciales.sql")
        for username, role in [("ana", "cliente"), ("ops", "admin")]:
            cur.execute(
                "INSERT INTO usuarios (username, email, full_name, password_hash, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (username, f"{username}@genx.test", username.title(),
                 generate_password_hash("password123"), role),
            )
    conn.commit()
    conn.close()

    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_query(app):
    """Consulta directa a la base de pruebas para verificar resultados."""
    def query(sql, params=None):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()
    return query


def login(client, username, role):
    return client.post("/login", data={"username": username, "password": "password123", "role": role})
