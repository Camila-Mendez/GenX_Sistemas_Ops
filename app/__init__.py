from dotenv import load_dotenv
from flask import Flask
from flask_wtf.csrf import CSRFProtect

from app.utilities.db import db

# Carga variables desde .env (si existe) antes de leer la configuración
load_dotenv()

app = Flask(__name__)

# Cargar configuración
app.config.from_object("app.config.Config")

# Base de datos y protección CSRF para todos los formularios
db.init_app(app)
csrf = CSRFProtect(app)

# Importar modelos, rutas y comandos (tienen que ir después de crear app)
from app import models, routes, cli  # noqa: E402,F401
