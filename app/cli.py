"""Comandos de administración.

    flask --app run init-db                      # crea tablas y planes base
    flask --app run create-user admin --role admin
"""
import click

from app import app
from app.models import ServicePlan, User
from app.utilities.db import db

DEFAULT_PLANS = [
    {
        "slug": "respaldo-programado",
        "name": "Respaldo Programado",
        "description": "Copias incrementales con rsync y cron hacia el servidor pasivo, "
                       "con retención de 30 días y reporte diario.",
        "rto": "4 horas", "rpo": "24 horas", "price_monthly": 45,
    },
    {
        "slug": "replicacion-drbd",
        "name": "Replicación en Tiempo Real",
        "description": "Bloque de almacenamiento replicado con DRBD (protocolo C) entre "
                       "nodo activo y pasivo. Cero pérdida de datos confirmados.",
        "rto": "30 minutos", "rpo": "≈ 0", "price_monthly": 120,
    },
    {
        "slug": "alta-disponibilidad",
        "name": "Alta Disponibilidad",
        "description": "DRBD + keepalived con IP virtual (VRRP). El nodo pasivo toma el "
                       "control automáticamente si el activo deja de responder.",
        "rto": "< 1 minuto", "rpo": "≈ 0", "price_monthly": 210,
    },
    {
        "slug": "hardening",
        "name": "Seguridad y Hardening",
        "description": "Reglas ufw, fail2ban, SSH solo por llave y auditoría de accesos "
                       "en ambos servidores Ubuntu.",
        "rto": "N/A", "rpo": "N/A", "price_monthly": 60,
    },
]


@app.cli.command("init-db")
def init_db():
    """Crea las tablas y carga los planes base (idempotente)."""
    db.create_all()
    created = 0
    for data in DEFAULT_PLANS:
        if not ServicePlan.query.filter_by(slug=data["slug"]).first():
            db.session.add(ServicePlan(**data))
            created += 1
    db.session.commit()
    click.echo(f"Tablas listas en {db.engine.dialect.name}. Planes nuevos: {created}.")


@app.cli.command("create-user")
@click.argument("username")
@click.option("--role", type=click.Choice(["admin", "cliente"]), default="cliente")
@click.option("--email", prompt=True)
@click.option("--full-name", prompt="Nombre completo")
@click.password_option(prompt="Contraseña")
def create_user(username, role, email, full_name, password):
    """Crea un usuario (los admin solo se crean por aquí)."""
    if User.query.filter((User.username == username) | (User.email == email)).first():
        raise click.ClickException("Ya existe un usuario con ese nombre o correo.")
    user = User(username=username, email=email, full_name=full_name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Usuario '{username}' creado con rol {role}.")
