"""Comandos de administración.

    flask --app run check-db                       # prueba la conexión a MySQL
    flask --app run create-user admin --role admin # crea un usuario con contraseña hasheada

Las tablas y los planes se crean en la VM con los scripts de sql/.
"""
import click
import pymysql
from werkzeug.security import generate_password_hash

from app import app
from app.utilities.db_connection import check_database, execute, fetch_one


@app.cli.command("check-db")
def check_db():
    """Verifica que la app pueda conectarse a MySQL."""
    ok, detail = check_database()
    if not ok:
        raise click.ClickException(f"No hay conexión con MySQL ({detail}). Revisa las variables DB_*.")
    plans = fetch_one("SELECT COUNT(*) AS n FROM planes")["n"]
    click.echo(f"Conexión correcta: {detail}. Planes cargados: {plans}.")


@app.cli.command("create-user")
@click.argument("username")
@click.option("--role", type=click.Choice(["admin", "cliente"]), default="cliente")
@click.option("--email", prompt=True)
@click.option("--full-name", prompt="Nombre completo")
@click.password_option(prompt="Contraseña")
def create_user(username, role, email, full_name, password):
    """Crea un usuario (los admin solo se crean por aquí)."""
    try:
        execute(
            "INSERT INTO usuarios (username, email, full_name, password_hash, role) "
            "VALUES (%s, %s, %s, %s, %s)",
            (username, email.strip().lower(), full_name, generate_password_hash(password), role),
        )
    except pymysql.err.IntegrityError:
        raise click.ClickException("Ya existe un usuario con ese nombre o correo.")
    click.echo(f"Usuario '{username}' creado con rol {role}.")
