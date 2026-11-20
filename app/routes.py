from datetime import datetime, timezone
from decimal import Decimal
from functools import wraps

from flask import (abort, flash, jsonify, redirect, render_template, request,
                   session, url_for)

from app import app
from app.models import (ContactMessage, LoginEvent, ServicePlan, ServiceRequest,
                        ServiceRequestItem, User)
from app.utilities.db import check_database, db, node_name

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


def solicitud_actual():
    """La 'solicitud' en sesión equivale al carrito: {slug: servidores}."""
    return session.setdefault("solicitud", {})


def detalle_solicitud():
    items, total = [], Decimal("0")
    data = solicitud_actual()
    if data:
        plans = ServicePlan.query.filter(ServicePlan.slug.in_(data.keys())).all()
        for plan in plans:
            servers = data[plan.slug]
            subtotal = plan.price_monthly * servers
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
    plans = ServicePlan.query.filter_by(active=True).order_by(ServicePlan.price_monthly).all()
    return render_template("servicios.html", plans=plans)


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

        db.session.add(ContactMessage(name=name, email=email, message=message,
                                      company=request.form.get("company", "").strip()))
        db.session.commit()
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

        user = User.query.filter_by(username=username).first()
        valid = user is not None and user.check_password(password)

        # 1. Registrar intento en la bitácora (incluye el nodo que respondió)
        db.session.add(LoginEvent(username=username[:50] or "-", success=valid,
                                  node=node_name(), ip_address=request.remote_addr))

        # 2. Validación de credenciales
        if not valid:
            db.session.commit()
            return render_template("login.html", error="Credenciales inválidas"), 401

        # 3. Validar tipo de acceso
        if role not in ROLES or user.role != role:
            db.session.commit()
            return render_template("login.html", error="Tipo de acceso incorrecto"), 403

        # 4. Guardar sesión
        user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role

        # 5. Redirección según tipo
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for(home_for(user.role)))

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
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            error = "El usuario o correo ya existe"

        if error:
            return render_template("register.html", error=error, form=form), 400

        user = User(username=username, email=email, full_name=full_name,
                    company=form.get("company", "").strip() or None, role="cliente")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
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
    stats = {
        "clientes": User.query.filter_by(role="cliente").count(),
        "solicitudes": ServiceRequest.query.count(),
        "pendientes": ServiceRequest.query.filter(
            ServiceRequest.status.in_(["Recibida", "En análisis"])).count(),
        "mensajes": ContactMessage.query.count(),
    }
    return render_template(
        "dashboard.html",
        username=session["username"],
        node=node_name(),
        db_ok=db_ok,
        db_detail=db_detail,
        stats=stats,
        events=LoginEvent.query.order_by(LoginEvent.created_at.desc()).limit(8).all(),
        requests=ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).limit(8).all(),
        messages=ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all(),
        statuses=REQUEST_STATUSES,
    )


@app.route("/dashboard/solicitud/<int:request_id>/estado", methods=["POST"])
@login_required("admin")
def update_request_status(request_id):
    sr = db.session.get(ServiceRequest, request_id) or abort(404)
    status = request.form.get("status")
    if status in REQUEST_STATUSES:
        sr.status = status
        db.session.commit()
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
    plans = ServicePlan.query.filter_by(active=True).order_by(ServicePlan.price_monthly).all()
    return render_template("planes.html", plans=plans, seleccion=solicitud_actual())


# ---------------------------------------------------------
# SOLICITUD — equivalente al carrito (cantidad = servidores cubiertos)
# ---------------------------------------------------------

@app.route("/solicitud/agregar/<slug>", methods=["POST"])
@login_required("cliente")
def agregar_plan(slug):
    if not ServicePlan.query.filter_by(slug=slug, active=True).first():
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
# CONFIRMAR — equivalente al checkout; aquí sí se guarda en BD
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

        sr = ServiceRequest(
            user_id=session["user_id"],
            site=site,
            contact_phone=request.form.get("contact_phone", "").strip() or None,
            notes=request.form.get("notes", "").strip() or None,
            total_monthly=total,
        )
        for item in items:
            sr.items.append(ServiceRequestItem(plan_id=item["plan"].id,
                                               servers=item["servers"],
                                               unit_price=item["plan"].price_monthly))
        db.session.add(sr)
        db.session.commit()
        session.pop("solicitud", None)
        return redirect(url_for("solicitud_enviada", request_id=sr.id))

    return render_template("confirmar.html", items=items, total=total)


@app.route("/solicitud-enviada/<int:request_id>")
@login_required("cliente")
def solicitud_enviada(request_id):
    sr = ServiceRequest.query.filter_by(id=request_id, user_id=session["user_id"]).first_or_404()
    return render_template("solicitud_enviada.html", sr=sr)


@app.route("/mis-solicitudes")
@login_required("cliente")
def mis_solicitudes():
    requests_ = (ServiceRequest.query.filter_by(user_id=session["user_id"])
                 .order_by(ServiceRequest.created_at.desc()).all())
    return render_template("mis_solicitudes.html", requests=requests_)


# ---------------------------------------------------------
# ERRORES
# ---------------------------------------------------------

@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404
