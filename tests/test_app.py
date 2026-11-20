from app.models import LoginEvent, ServiceRequest, User
from tests.conftest import login


def test_public_pages(client):
    for path in ["/", "/servicios", "/nosotros", "/contacto", "/login", "/register"]:
        assert client.get(path).status_code == 200, path
    assert client.get("/no-existe").status_code == 404


def test_health_reports_node(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"node": "nodo-test", "database": "ok", "engine": "sqlite"}


def test_login_redirects_by_role(client):
    assert login(client, "ops", "admin").headers["Location"] == "/dashboard"
    client.get("/logout")
    assert login(client, "ana", "cliente").headers["Location"] == "/planes"


def test_login_errors_and_audit(client, app):
    assert client.post("/login", data={"username": "ana", "password": "mala", "role": "cliente"}).status_code == 401
    assert login(client, "ana", "admin").status_code == 403
    with app.app_context():
        events = LoginEvent.query.all()
        assert [e.success for e in events] == [False, True]
        assert all(e.node == "nodo-test" for e in events)


def test_role_protection(client):
    assert client.get("/dashboard").headers["Location"].startswith("/login")
    login(client, "ana", "cliente")
    assert client.get("/dashboard").headers["Location"] == "/planes"


def test_register_creates_cliente(client, app):
    res = client.post("/register", data={
        "username": "nuevo", "email": "Nuevo@genx.test", "full_name": "Nuevo",
        "password": "secreto123", "password_confirm": "secreto123"})
    assert res.status_code == 302
    with app.app_context():
        user = User.query.filter_by(username="nuevo").one()
        assert user.role == "cliente" and user.email == "nuevo@genx.test"
        assert user.password_hash != "secreto123"
    assert client.post("/register", data={
        "username": "nuevo", "email": "x@genx.test", "full_name": "X",
        "password": "secreto123", "password_confirm": "secreto123"}).status_code == 400


def test_request_flow_persists(client, app):
    login(client, "ana", "cliente")
    client.post("/solicitud/agregar/alta-disponibilidad")
    client.post("/solicitud/agregar/alta-disponibilidad")
    client.post("/solicitud/agregar/hardening")
    client.post("/solicitud/actualizar/hardening/decrease")  # elimina hardening
    res = client.post("/confirmar", data={"site": "San José"})
    assert res.status_code == 302
    with app.app_context():
        sr = ServiceRequest.query.one()
        assert sr.total_monthly == 420
        assert [(i.plan.slug, i.servers) for i in sr.items] == [("alta-disponibilidad", 2)]
    assert b"Solicitud #1" in client.get(res.headers["Location"]).data

    client.get("/logout")
    login(client, "ops", "admin")
    client.post(f"/dashboard/solicitud/{sr.id}/estado", data={"status": "Activa"})
    with app.app_context():
        assert ServiceRequest.query.one().status == "Activa"
