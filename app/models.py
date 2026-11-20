from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.utilities.db import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------
# USUARIOS
# Los "admin" van al panel de operaciones (dashboard)
# Los "cliente" van al portal de planes y solicitudes
# ---------------------------------------------------------

class User(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="cliente")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_login = db.Column(db.DateTime)

    requests = db.relationship("ServiceRequest", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class LoginEvent(db.Model):
    """Bitácora de inicios de sesión: guarda qué nodo atendió cada intento."""
    __tablename__ = "bitacora_login"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    node = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)


# ---------------------------------------------------------
# CATÁLOGO DE PLANES DR
# ---------------------------------------------------------

class ServicePlan(db.Model):
    __tablename__ = "planes"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    rto = db.Column(db.String(30), nullable=False)   # Recovery Time Objective
    rpo = db.Column(db.String(30), nullable=False)   # Recovery Point Objective
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False)  # por servidor
    active = db.Column(db.Boolean, nullable=False, default=True)


# ---------------------------------------------------------
# SOLICITUDES DE SERVICIO (equivalente a los pedidos)
# ---------------------------------------------------------

class ServiceRequest(db.Model):
    __tablename__ = "solicitudes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    site = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(30))
    notes = db.Column(db.String(1000))
    status = db.Column(db.String(30), nullable=False, default="Recibida")
    total_monthly = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="requests")
    items = db.relationship("ServiceRequestItem", back_populates="request",
                            cascade="all, delete-orphan")


class ServiceRequestItem(db.Model):
    __tablename__ = "solicitud_detalle"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("solicitudes.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("planes.id"), nullable=False)
    servers = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    request = db.relationship("ServiceRequest", back_populates="items")
    plan = db.relationship("ServicePlan")


class ContactMessage(db.Model):
    __tablename__ = "mensajes_contacto"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120))
    message = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
