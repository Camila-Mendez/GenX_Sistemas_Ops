from tests.conftest import login


def test_public_pages(client):
    for path in ["/", "/servicios", "/nosotros", "/contacto", "/login", "/register"]:
        assert client.get(path).status_code == 200, path
    assert client.get("/no-existe").status_code == 404


def test_servicios_lists_plans_from_script(client):
    assert b"Alta Disponibilidad" in client.get("/servicios").data


def test_health_reports_node(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["node"] == "nodo-test" and data["database"] == "ok"
    assert data["engine"].startswith("MySQL")


def test_login_redirects_by_role(client):
    assert login(client, "ops", "admin").headers["Location"] == "/dashboard"
    client.get("/logout")
    assert login(client, "ana", "cliente").headers["Location"] == "/planes"


def test_login_errors_and_audit(client, db_query):
    assert client.post("/login", data={"username": "ana", "password": "mala", "role": "cliente"}).status_code == 401
    assert login(client, "ana", "admin").status_code == 403
    events = db_query("SELECT success, node FROM bitacora_login ORDER BY id")
    assert [e["success"] for e in events] == [0, 1]
    assert all(e["node"] == "nodo-test" for e in events)


def test_role_protection(client):
    assert client.get("/dashboard").headers["Location"].startswith("/login")
    login(client, "ana", "cliente")
    assert client.get("/dashboard").headers["Location"] == "/planes"


def test_register_creates_cliente(client, db_query):
    res = client.post("/register", data={
        "username": "nuevo", "email": "Nuevo@genx.test", "full_name": "Nuevo",
        "password": "secreto123", "password_confirm": "secreto123"})
    assert res.status_code == 302
    user = db_query("SELECT role, email, password_hash FROM usuarios WHERE username = 'nuevo'")[0]
    assert user["role"] == "cliente" and user["email"] == "nuevo@genx.test"
    assert user["password_hash"] != "secreto123"
    assert client.post("/register", data={
        "username": "nuevo", "email": "x@genx.test", "full_name": "X",
        "password": "secreto123", "password_confirm": "secreto123"}).status_code == 400


def test_contact_message_saved(client, db_query):
    client.post("/contacto", data={"name": "Luis", "email": "l@x.test", "message": "Hola"})
    assert db_query("SELECT name FROM mensajes_contacto")[0]["name"] == "Luis"


def test_request_flow_persists(client, db_query):
    login(client, "ana", "cliente")
    client.post("/solicitud/agregar/alta-disponibilidad")
    client.post("/solicitud/agregar/alta-disponibilidad")
    client.post("/solicitud/agregar/hardening")
    client.post("/solicitud/actualizar/hardening/decrease")  # elimina hardening
    res = client.post("/confirmar", data={"site": "San José"})
    assert res.status_code == 302

    sr = db_query("SELECT id, total_monthly FROM solicitudes")[0]
    assert sr["total_monthly"] == 420
    lines = db_query("SELECT p.slug, d.servers FROM solicitud_detalle d JOIN planes p ON p.id = d.plan_id")
    assert [(l["slug"], l["servers"]) for l in lines] == [("alta-disponibilidad", 2)]
    assert f"Solicitud #{sr['id']}".encode() in client.get(res.headers["Location"]).data
    assert b"Alta Disponibilidad" in client.get("/mis-solicitudes").data

    client.get("/logout")
    login(client, "ops", "admin")
    assert b"San Jos" in client.get("/dashboard").data
    client.post(f"/dashboard/solicitud/{sr['id']}/estado", data={"status": "Activa"})
    assert db_query("SELECT status FROM solicitudes")[0]["status"] == "Activa"
