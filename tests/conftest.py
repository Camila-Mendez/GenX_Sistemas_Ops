import os

os.environ["DATABASE_URL"] = "sqlite://"  # base en memoria para pruebas
os.environ["GENX_NODE_NAME"] = "nodo-test"

import pytest  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import app as flask_app  # noqa: E402
from app.cli import DEFAULT_PLANS  # noqa: E402
from app.models import ServicePlan, User  # noqa: E402
from app.utilities.db import db  # noqa: E402


@pytest.fixture()
def app():
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False,
                            SQLALCHEMY_ENGINE_OPTIONS={"poolclass": StaticPool})
    with flask_app.app_context():
        db.create_all()
        for plan in DEFAULT_PLANS:
            db.session.add(ServicePlan(**plan))
        for username, role in [("ana", "cliente"), ("ops", "admin")]:
            u = User(username=username, email=f"{username}@genx.test", full_name=username.title(), role=role)
            u.set_password("password123")
            db.session.add(u)
        db.session.commit()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username, role):
    return client.post("/login", data={"username": username, "password": "password123", "role": role})
