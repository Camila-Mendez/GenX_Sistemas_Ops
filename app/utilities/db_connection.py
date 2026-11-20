"""Script de conexión a MySQL.

Es el único punto de acceso a la base de datos de la aplicación: abre la
conexión con PyMySQL y ejecuta SQL directo. El modelo físico (tablas,
llaves, datos iniciales) NO se crea desde aquí; se crea en la VM con los
scripts de la carpeta sql/.
"""
import os

import pymysql
from flask import g
from pymysql.cursors import DictCursor


def get_connection():
    """Abre una conexión nueva usando las variables de entorno DB_*."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        # Se envía en UTF-8: PyMySQL usa latin-1 por defecto y fallaría con tildes o ñ
        password=os.getenv("DB_PASSWORD", "").encode("utf-8"),
        database=os.getenv("DB_NAME", "genx_portal"),
        charset="utf8mb4",
        cursorclass=DictCursor,   # cada fila llega como diccionario
        autocommit=False,
        connect_timeout=5,
    )


# ---------------------------------------------------------
# Una conexión por petición HTTP (se cierra al terminar)
# ---------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = get_connection()
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)


# ---------------------------------------------------------
# Helpers para ejecutar SQL (siempre con parámetros %s, nunca concatenando)
# ---------------------------------------------------------

def fetch_one(sql, params=None):
    with get_db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetch_all(sql, params=None):
    with get_db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute(sql, params=None, commit=True):
    """INSERT / UPDATE / DELETE. Devuelve el id generado (lastrowid)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            last_id = cur.lastrowid
        if commit:
            conn.commit()
        return last_id
    except Exception:
        conn.rollback()
        raise


def commit():
    get_db().commit()


def rollback():
    get_db().rollback()


def check_database():
    """Devuelve (ok, detalle). Lo usan /health y el panel."""
    try:
        row = fetch_one("SELECT VERSION() AS version")
        return True, f"MySQL {row['version']}"
    except Exception as exc:  # noqa: BLE001 - se informa el tipo de error
        close_db()
        return False, exc.__class__.__name__
