from datetime import datetime, timezone
from decimal import Decimal
from functools import wraps
import socket

import pymysql
from flask import (abort, current_app, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from app import app
from app.utilities.db_connection import (check_database, commit, execute, fetch_all,
                                         fetch_one, rollback)

ROLES = {"admin", "cliente"}
REQUEST_STATUSES = ["Recibida", "En análisis", "En implementación", "Activa", "Cancelada"]


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def login_required(role=None):
    """Protege una ruta. Si se indica rol, solo ese rol puede entrar."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login", next=request.path))
            if role and session.get("role") != role:
                return redirect(url_for(home_for(session.get("role"))))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def home_for(role):
    return "dashboard" if role == "admin" else "planes"


def node_name():
    """Nombre del servidor que atiende la petición (sirve para ver el failover)."""
    return current_app.config.get("NODE_NAME") or socket.gethostname()


def active_plans():
    return fetch_all("SELECT * FROM planes WHERE active = TRUE ORDER BY price_monthly")


def solicitud_actual():
    """La 'solicitud' en sesión equivale al carrito: {slug: servidores}."""
    return session.setdefault("solicitud", {})


def detalle_solicitud():
    items, total = [], Decimal("0")
    data = solicitud_actual()
    if data:
        placeholders = ", ".join(["%s"] * len(data))
        plans = fetch_all(
            f"SELECT * FROM planes WHERE active = TRUE AND slug IN ({placeholders}) "
            "ORDER BY price_monthly",
            tuple(data.keys()),
        )
        for plan in plans:
            servers = data[plan["slug"]]
            subtotal = plan["price_monthly"] * servers
            total += subtotal
            items.append({"plan": plan, "servers": servers, "subtotal": subtotal})
    return items, total


@app.context_processor
def inject_globals():
    return {
        "current_year": datetime.now(timezone.utc).year,
        "solicitud_count": sum(session.get("solicitud", {}).values()),
    }


# ---------------------------------------------------------
#  PUBLIC ROUTES
# ---------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/servicios")
def servicios():
    return render_template("servicios.html", plans=active_plans())


@app.route("/nosotros")
def nosotros():
    return render_template("nosotros.html")


@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            flash("Completa nombre, correo y mensaje.", "error")
            return render_template("contacto.html", form=request.form), 400

        execute(
            "INSERT INTO mensajes_contacto (name, email, company, message) VALUES (%s, %s, %s, %s)",
            (name, email, request.form.get("company", "").strip() or None, message),
        )
        flash("Gracias, un ingeniero de GenX te contactará pronto.", "success")
        return redirect(url_for("contacto"))

    return render_template("contacto.html", form={})


@app.route("/health")
def health():
    """Usado por keepalived (track_script) o monitoreo para saber si el nodo sirve."""
    ok, detail = check_database()
    payload = {"node": node_name(), "database": "ok" if ok else "error", "engine": detail}
    return jsonify(payload), (200 if ok else 503)


# ---------------------------------------------------------
# LOGIN (two types)
# ---------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role")  # admin o cliente

        user = fetch_one(
            "SELECT id, username, password_hash, role FROM usuarios WHERE username = %s",
            (username,),
        )
        valid = user is not None and check_password_hash(user["password_hash"], password)

        # 1. Registrar intento en la bitácora (incluye el nodo que respondió)
        execute(
            "INSERT INTO bitacora_login (username, success, node, ip_address) VALUES (%s, %s, %s, %s)",
            (username[:50] or "-", valid, node_name(), request.remote_addr),
        )

        # 2. Validación de credenciales
        if not valid:
            return render_template("login.html", error="Credenciales inválidas"), 401

        # 3. Validar tipo de acceso
        if role not in ROLES or user["role"] != role:
            return render_template("login.html", error="Tipo de acceso incorrecto"), 403

        # 4. Guardar sesión
        execute("UPDATE usuarios SET last_login = NOW() WHERE id = %s", (user["id"],))
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        # 5. Redirección según tipo
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for(home_for(user["role"])))

    return render_template("login.html")


# ---------------------------------------------------------
# REGISTER (solo clientes; los admin se crean con `flask create-user`)
# ---------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = request.form
        username = form.get("username", "").strip()
        email = form.get("email", "").strip().lower()
        full_name = form.get("full_name", "").strip()
        password = form.get("password", "")

        error = None
        if not all([username, email, full_name, password]):
            error = "Todos los campos marcados son obligatorios"
        elif len(password) < 8:
            error = "La contraseña debe tener al menos 8 caracteres"
        elif password != form.get("password_confirm"):
            error = "Las contraseñas no coinciden"

        if not error:
            try:
                execute(
                    "INSERT INTO usuarios (username, email, full_name, company, password_hash, role) "
                    "VALUES (%s, %s, %s, %s, %s, 'cliente')",
                    (username, email, full_name, form.get("company", "").strip() or None,
                     generate_password_hash(password)),
                )
            except pymysql.err.IntegrityError:
                error = "El usuario o correo ya existe"

        if error:
            return render_template("register.html", error=error, form=form), 400

        flash("Cuenta creada. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form={})


# ---------------------------------------------------------
# DASHBOARD DE OPERACIONES (ONLY admin)
# ---------------------------------------------------------

@app.route("/dashboard")
@login_required("admin")
def dashboard():
    db_ok, db_detail = check_database()
    stats = fetch_one("""
        SELECT
          (SELECT COUNT(*) FROM usuarios WHERE role = 'cliente')                           AS clientes,
          (SELECT COUNT(*) FROM solicitudes)                                               AS solicitudes,
          (SELECT COUNT(*) FROM solicitudes WHERE status IN ('Recibida', 'En análisis'))   AS pendientes,
          (SELECT COUNT(*) FROM mensajes_contacto)                                         AS mensajes
    """)
    requests_ = fetch_all("""
        SELECT s.id, s.site, s.status, s.total_monthly, s.created_at,
               u.full_name, u.company, u.email
        FROM solicitudes s
        JOIN usuarios u ON u.id = s.user_id
        ORDER BY s.created_at DESC, s.id DESC
        LIMIT 8
    """)
    return render_template(
        "dashboard.html",
        username=session["username"],
        node=node_name(),
        db_ok=db_ok,
        db_detail=db_detail,
        stats=stats,
        events=fetch_all("SELECT * FROM bitacora_login ORDER BY id DESC LIMIT 8"),
        requests=requests_,
        messages=fetch_all("SELECT * FROM mensajes_contacto ORDER BY id DESC LIMIT 5"),
        statuses=REQUEST_STATUSES,
    )


@app.route("/dashboard/solicitud/<int:request_id>/estado", methods=["POST"])
@login_required("admin")
def update_request_status(request_id):
    status = request.form.get("status")
    if status in REQUEST_STATUSES:
        execute("UPDATE solicitudes SET status = %s WHERE id = %s", (status, request_id))
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------
# PLANES (clientes ONLY) — equivalente a la tienda
# ---------------------------------------------------------

@app.route("/planes")
@login_required("cliente")
def planes():
    return render_template("planes.html", plans=active_plans(), seleccion=solicitud_actual())


# ---------------------------------------------------------
# SOLICITUD — equivalente al carrito (cantidad = servidores cubiertos)
# ---------------------------------------------------------

@app.route("/solicitud/agregar/<slug>", methods=["POST"])
@login_required("cliente")
def agregar_plan(slug):
    if not fetch_one("SELECT id FROM planes WHERE slug = %s AND active = TRUE", (slug,)):
        abort(404)
    data = solicitud_actual()
    data[slug] = data.get(slug, 0) + 1
    session.modified = True
    flash("Plan agregado a tu solicitud.", "success")
    return redirect(url_for("planes"))


@app.route("/solicitud")
@login_required("cliente")
def solicitud():
    items, total = detalle_solicitud()
    return render_template("solicitud.html", items=items, total=total)


@app.route("/solicitud/quitar/<slug>", methods=["POST"])
@login_required("cliente")
def quitar_plan(slug):
    solicitud_actual().pop(slug, None)
    session.modified = True
    return redirect(url_for("solicitud"))


@app.route("/solicitud/actualizar/<slug>/<action>", methods=["POST"])
@login_required("cliente")
def actualizar_plan(slug, action):
    data = solicitud_actual()
    if slug in data:
        if action == "increase":
            data[slug] += 1
        elif action == "decrease":
            data[slug] -= 1
            if data[slug] <= 0:
                del data[slug]
        session.modified = True
    return redirect(url_for("solicitud"))


# ---------------------------------------------------------
# CONFIRMAR — equivalente al checkout; aquí sí se guarda en MySQL
# ---------------------------------------------------------

@app.route("/confirmar", methods=["GET", "POST"])
@login_required("cliente")
def confirmar():
    items, total = detalle_solicitud()
    if not items:
        return redirect(url_for("planes"))

    if request.method == "POST":
        site = request.form.get("site", "").strip()
        if not site:
            return render_template("confirmar.html", items=items, total=total,
                                   error="Indica la sede o centro de datos"), 400

        # Encabezado + detalle en una sola transacción
        try:
            request_id = execute(
                "INSERT INTO solicitudes (user_id, site, contact_phone, notes, total_monthly) "
                "VALUES (%s, %s, %s, %s, %s)",
                (session["user_id"], site,
                 request.form.get("contact_phone", "").strip() or None,
                 request.form.get("notes", "").strip() or None,
                 total),
                commit=False,
            )
            for item in items:
                execute(
                    "INSERT INTO solicitud_detalle (request_id, plan_id, servers, unit_price) "
                    "VALUES (%s, %s, %s, %s)",
                    (request_id, item["plan"]["id"], item["servers"], item["plan"]["price_monthly"]),
                    commit=False,
                )
            commit()
        except Exception:
            rollback()
            raise

        session.pop("solicitud", None)
        return redirect(url_for("solicitud_enviada", request_id=request_id))

    return render_template("confirmar.html", items=items, total=total)


@app.route("/solicitud-enviada/<int:request_id>")
@login_required("cliente")
def solicitud_enviada(request_id):
    sr = fetch_one("SELECT * FROM solicitudes WHERE id = %s AND user_id = %s",
                   (request_id, session["user_id"]))
    if not sr:
        abort(404)
    return render_template("solicitud_enviada.html", sr=sr)


@app.route("/mis-solicitudes")
@login_required("cliente")
def mis_solicitudes():
    requests_ = fetch_all(
        "SELECT * FROM solicitudes WHERE user_id = %s ORDER BY created_at DESC, id DESC",
        (session["user_id"],),
    )
    lines = fetch_all("""
        SELECT d.request_id, d.servers, d.unit_price, p.name
        FROM solicitud_detalle d
        JOIN planes p ON p.id = d.plan_id
        JOIN solicitudes s ON s.id = d.request_id
        WHERE s.user_id = %s
        ORDER BY d.id
    """, (session["user_id"],))
    for sr in requests_:
        sr["detalle"] = [line for line in lines if line["request_id"] == sr["id"]]
    return render_template("mis_solicitudes.html", requests=requests_)


# ---------------------------------------------------------
# ERRORES
# ---------------------------------------------------------

@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404
